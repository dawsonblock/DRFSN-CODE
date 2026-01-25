"""Explainer - Human-readable reasoning generation.

Consumes execution artifacts and produces clear, structured Markdown
summaries explaining WHAT changed and WHY.
"""

from __future__ import annotations

from typing import Dict, Any, List


class Explainer:
    """Generates explanations for plan execution."""
    
    def explain_plan(self, plan_summary: Dict[str, Any], steps: List[Dict[str, Any]]) -> str:
        """Generate a full markdown explanation of the plan."""
        lines = [
            f"# Execution Report: {plan_summary.get('goal', 'Unknown Goal')}",
            "",
            f"**Status**: {'Complete' if plan_summary.get('is_complete') else 'Incomplete'}",
            f"**Steps**: {plan_summary.get('total_steps', 0)}",
            "",
            "## Decision Log",
            ""
        ]
        
        for step in steps:
            lines.append(self._explain_step(step))
            
        return "\n".join(lines)
        
    def _explain_step(self, step: Dict[str, Any]) -> str:
        """Explain a single step."""
        title = step.get("title", "Unknown Step")
        intent = step.get("intent", "")
        status = step.get("status", "PENDING")
        outcome = step.get("result", {})
        
        icon = "✅" if status == "DONE" else "❌" if status == "FAILED" else "⏳"
        
        md = [
            f"### {icon} {title}",
            "",
            f"**Intent**: {intent}",
            f"**Status**: {status}",
        ]
        
        if outcome and not outcome.get("success", False):
            err = outcome.get("error_message", "Unknown error")
            md.append(f"**Failure**: {err}")
            
        if step.get("hypothesis"):
            md.append(f"**Hypothesis**: {step['hypothesis']}")
            
        md.append("")
        return "\n".join(md)
