"""LLM Decomposer - Intelligent goal decomposition using LLM.

Uses LLM to decompose high-level goals into structured, atomic steps.
Falls back to pattern-based decomposition on LLM failure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .schema import Plan, RiskLevel, Step


@dataclass
class DecompositionConfig:
    """Configuration for LLM decomposition."""
    
    temperature: float = 0.3
    max_tokens: int = 2000
    max_retries: int = 2
    timeout_sec: float = 30.0
    min_steps: int = 2
    max_steps: int = 10
    require_verification: bool = True


# Type alias for LLM call function
LLMCallFn = Callable[[str, float, int], str]


DECOMPOSITION_SYSTEM_PROMPT = """You are a software engineering planner. Your job is to decompose high-level goals into atomic, executable steps.

RULES:
1. Each step must be independently executable
2. Steps must have clear success criteria
3. Higher-risk steps (modifying core files) need rollback hints
4. Each step must specify which files it may touch
5. Steps should be ordered by dependencies
6. Include verification commands where applicable

FORBIDDEN FILES (never include):
- controller.py, safety.py, rules.py
- *.env, secrets/*, credentials/*
- node_modules/*, __pycache__/*

RISK LEVELS:
- LOW: Read-only analysis, documentation, simple edits
- MED: Modifying test files, adding new files
- HIGH: Modifying core logic, refactoring existing code

OUTPUT FORMAT (JSON array):
[
  {
    "step_id": "analyze-failure",
    "title": "Analyze test failure",
    "intent": "Understand why the test is failing by examining the error message and test code",
    "allowed_files": ["tests/test_example.py", "src/module.py"],
    "success_criteria": "Root cause of failure identified",
    "dependencies": [],
    "verify": "python -c 'import src.module'",
    "risk_level": "LOW",
    "rollback_hint": ""
  },
  ...
]
"""


DECOMPOSITION_USER_PROMPT = """Goal: {goal}

Context:
- Repository type: {repo_type}
- Primary language: {language}
- Test command: {test_cmd}
- Failing tests: {failing_tests}
- Additional context: {extra_context}

Decompose this goal into {min_steps}-{max_steps} atomic, ordered steps.
Output ONLY valid JSON array of steps, no explanation."""


class LLMDecomposer:
    """Uses LLM to decompose goals into structured plans."""
    
    def __init__(
        self,
        llm_call: Optional[LLMCallFn] = None,
        config: Optional[DecompositionConfig] = None,
    ):
        """Initialize the decomposer.
        
        Args:
            llm_call: Function to call LLM. Signature: (prompt, temperature, max_tokens) -> response
            config: Decomposition configuration.
        """
        self._llm_call = llm_call
        self._config = config or DecompositionConfig()
    
    def decompose(
        self,
        goal: str,
        context: Dict[str, Any],
        plan_id: str,
    ) -> Optional[Plan]:
        """Decompose a goal into a structured plan using LLM.
        
        Args:
            goal: The high-level goal description.
            context: Execution context (repo_type, language, test_cmd, etc.)
            plan_id: ID for the generated plan.
            
        Returns:
            Plan if successful, None if LLM fails or returns invalid response.
        """
        if self._llm_call is None:
            return None
        
        prompt = self._build_decomposition_prompt(goal, context)
        
        for attempt in range(self._config.max_retries):
            try:
                response = self._llm_call(
                    prompt,
                    self._config.temperature,
                    self._config.max_tokens,
                )
                
                steps = self._parse_llm_response(response)
                
                if steps and self._validate_decomposition(steps):
                    return self._build_plan(plan_id, goal, steps, context)
                    
            except Exception:
                # LLM call failed, try again or fall back
                continue
        
        return None
    
    def _build_decomposition_prompt(self, goal: str, context: Dict[str, Any]) -> str:
        """Build the decomposition prompt for the LLM.
        
        Args:
            goal: The goal to decompose.
            context: Execution context.
            
        Returns:
            Formatted prompt string.
        """
        # Extract context values
        repo_type = context.get("repo_type", "unknown")
        language = context.get("language", "python")
        test_cmd = context.get("test_cmd", "pytest")
        failing_tests = context.get("failing_tests", [])
        
        # Build extra context string
        extra_parts = []
        if context.get("target_file"):
            extra_parts.append(f"Target file: {context['target_file']}")
        if context.get("error_message"):
            extra_parts.append(f"Error: {context['error_message'][:200]}")
        if context.get("issue_text"):
            extra_parts.append(f"Issue: {context['issue_text'][:300]}")
        extra_context = "; ".join(extra_parts) if extra_parts else "None"
        
        user_prompt = DECOMPOSITION_USER_PROMPT.format(
            goal=goal,
            repo_type=repo_type,
            language=language,
            test_cmd=test_cmd,
            failing_tests=", ".join(failing_tests) if failing_tests else "None",
            extra_context=extra_context,
            min_steps=self._config.min_steps,
            max_steps=self._config.max_steps,
        )
        
        return f"{DECOMPOSITION_SYSTEM_PROMPT}\n\n{user_prompt}"
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into step dictionaries.
        
        Args:
            response: Raw LLM response.
            
        Returns:
            List of step dictionaries.
        """
        # Try to extract JSON from response
        # Handle cases where LLM adds explanation before/after JSON
        
        # Look for JSON array
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing the entire response as JSON
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        
        return []
    
    def _validate_decomposition(self, steps: List[Dict[str, Any]]) -> bool:
        """Validate the decomposition meets requirements.
        
        Args:
            steps: List of step dictionaries from LLM.
            
        Returns:
            True if valid, False otherwise.
        """
        if len(steps) < self._config.min_steps:
            return False
        if len(steps) > self._config.max_steps:
            return False
        
        required_fields = ["step_id", "title", "intent", "allowed_files", "success_criteria"]
        
        for step in steps:
            # Check required fields
            for field in required_fields:
                if field not in step:
                    return False
            
            # Check for forbidden files
            for f in step.get("allowed_files", []):
                if any(forbidden in f for forbidden in ["controller.py", "safety.py", ".env", "secrets/"]):
                    return False
        
        return True
    
    def _build_plan(
        self,
        plan_id: str,
        goal: str,
        step_dicts: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Plan:
        """Build a Plan from validated step dictionaries.
        
        Args:
            plan_id: Plan identifier.
            goal: Original goal.
            step_dicts: Validated step dictionaries.
            context: Execution context.
            
        Returns:
            Constructed Plan.
        """
        from datetime import datetime, timezone
        
        steps = []
        for step_dict in step_dicts:
            risk_str = step_dict.get("risk_level", "LOW").upper()
            try:
                risk = RiskLevel(risk_str)
            except ValueError:
                risk = RiskLevel.LOW
            
            step = Step(
                step_id=step_dict["step_id"],
                title=step_dict["title"],
                intent=step_dict["intent"],
                allowed_files=step_dict.get("allowed_files", []),
                success_criteria=step_dict.get("success_criteria", ""),
                dependencies=step_dict.get("dependencies", []),
                inputs=step_dict.get("inputs", []),
                verify=step_dict.get("verify", ""),
                risk_level=risk,
                rollback_hint=step_dict.get("rollback_hint", ""),
            )
            steps.append(step)
        
        return Plan(
            plan_id=plan_id,
            goal=goal,
            steps=steps,
            created_at=datetime.now(timezone.utc).isoformat(),
            assumptions=["LLM-generated decomposition"],
            constraints=context.get("constraints", []),
        )
    
    def get_prompt_template(self) -> str:
        """Get the system prompt template for debugging/inspection."""
        return DECOMPOSITION_SYSTEM_PROMPT


class DecompositionFallback:
    """Manages fallback between LLM and pattern-based decomposition."""
    
    def __init__(
        self,
        llm_decomposer: Optional[LLMDecomposer] = None,
        pattern_decomposer: Optional[Callable] = None,
    ):
        """Initialize with decomposers.
        
        Args:
            llm_decomposer: LLM-based decomposer.
            pattern_decomposer: Pattern-based fallback function.
        """
        self._llm = llm_decomposer
        self._pattern = pattern_decomposer
        self._last_source = "none"
    
    def decompose(
        self,
        goal: str,
        context: Dict[str, Any],
        plan_id: str,
    ) -> Optional[Plan]:
        """Decompose with fallback.
        
        Tries LLM first, falls back to pattern-based.
        
        Args:
            goal: The goal to decompose.
            context: Execution context.
            plan_id: Plan identifier.
            
        Returns:
            Plan if either method succeeds, None otherwise.
        """
        # Try LLM first
        if self._llm:
            plan = self._llm.decompose(goal, context, plan_id)
            if plan:
                self._last_source = "llm"
                return plan
        
        # Fall back to pattern-based
        if self._pattern:
            plan = self._pattern(goal, context, plan_id)
            if plan:
                self._last_source = "pattern"
                return plan
        
        self._last_source = "none"
        return None
    
    @property
    def last_source(self) -> str:
        """Get the source of the last successful decomposition."""
        return self._last_source
