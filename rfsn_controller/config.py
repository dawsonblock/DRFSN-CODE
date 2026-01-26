"""Unified configuration schema for the RFSN controller.

This module defines the central configuration dataclass that captures all
controller settings. All configuration is explicit and typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class ContractConfig:
    """Configuration for feature contracts.
    
    Controls which contracts are enabled and their behavior.
    """
    
    enabled: bool = True  # Whether contract system is enabled
    shell_execution_enabled: bool = True  # Enable shell execution contract
    budget_tracking_enabled: bool = True  # Enable budget tracking contract
    llm_calling_enabled: bool = True  # Enable LLM calling contract
    event_logging_enabled: bool = True  # Enable event logging contract
    strict_mode: bool = False  # Raise on violations vs. log warning
    log_violations: bool = True  # Log contract violations to events


@dataclass
class EventConfig:
    """Configuration for structured event logging.
    
    Controls event storage, retention, and filtering behavior.
    """
    
    enabled: bool = True  # Whether event logging is enabled
    storage_path: str = ".rfsn/events.jsonl"  # Path for event persistence
    max_events_memory: int = 10000  # Max events in memory (0 = unlimited)
    max_events_storage: int = 100000  # Max events in storage before rotation
    min_severity: str = "debug"  # Minimum severity to log: debug, info, warning, error, critical
    persist_events: bool = True  # Whether to persist events to storage
    include_subprocess: bool = True  # Log subprocess executions
    include_llm_calls: bool = True  # Log LLM API calls
    include_budget: bool = True  # Log budget events


@dataclass
class BudgetConfig:
    """Configuration for resource budget limits.
    
    Set any limit to 0 to disable that particular constraint.
    """
    
    max_steps: int = 0  # Maximum main loop iterations (0 = unlimited)
    max_llm_calls: int = 0  # Maximum LLM API calls (0 = unlimited)
    max_tokens: int = 0  # Maximum total tokens (0 = unlimited)
    max_time_seconds: float = 0  # Maximum execution time in seconds (0 = unlimited)
    max_subprocess_calls: int = 0  # Maximum subprocess calls (0 = unlimited)
    warning_threshold: float = 0.8  # Percentage at which warnings are triggered


@dataclass
class SandboxConfig:
    """Configuration for the sandbox execution environment."""
    
    image: str = "python:3.11-slim"
    mounts: List[str] = field(default_factory=list)
    cpu_limit: float = 2.0
    mem_limit: str = "2g"
    network_access: bool = False  # Default: no network inside sandbox


@dataclass
class ControllerConfig:
    """Central configuration for the RFSN controller.
    
    All settings are explicit and typed. This dataclass is immutable after
    creation to prevent configuration drift during execution.
    """
    
    # Repository settings
    repo_url: str = ""
    repo_ref: Optional[str] = None
    
    # Execution mode
    feature_mode: Literal["analysis", "repair", "refactor", "feature"] = "repair"
    
    # Test configuration
    test_command: str = "pytest -q"
    
    # Limits
    max_steps: int = 12
    max_steps_without_progress: int = 10
    
    # Sandbox settings
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    
    # Budget settings
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    
    # Event logging settings
    events: EventConfig = field(default_factory=EventConfig)
    
    # Contract settings
    contracts: ContractConfig = field(default_factory=ContractConfig)
    
    # Learning and policy
    learning_db_path: Optional[str] = None
    policy_mode: Literal["off", "bandit"] = "off"
    
    # Planning
    planner_mode: Literal["off", "v2", "dag"] = "v2"
    
    # Repo indexing
    repo_index_mode: Literal["off", "on"] = "off"
    
    # State directory (unified learning + audit)
    state_dir: str = ".rfsn"
    
    # Determinism
    seed: int = 1337
    
    # Model selection
    model: str = "deepseek-chat"
    
    # Output paths
    output_dir: str = ".rfsn"
    events_file: str = "events.jsonl"
    plan_file: str = "plan.json"
    eval_file: str = "eval.json"
    
    # Feature flags
    collect_finetuning_data: bool = False
    parallel_patches: bool = False
    enable_llm_cache: bool = False
    no_eval: bool = False
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        if self.seed < 0:
            raise ValueError("seed must be >= 0")
        if self.feature_mode not in ("analysis", "repair", "refactor", "feature"):
            raise ValueError(f"Invalid feature_mode: {self.feature_mode}")


def config_from_cli_args(args) -> ControllerConfig:
    """Create a ControllerConfig from parsed CLI arguments.
    
    Args:
        args: Namespace from argparse.
        
    Returns:
        Configured ControllerConfig instance.
    """
    sandbox = SandboxConfig(
        image=getattr(args, "sandbox_image", "python:3.11-slim"),
        network_access=getattr(args, "network_access", False),
    )
    
    budget = BudgetConfig(
        max_steps=getattr(args, "budget_max_steps", 0),
        max_llm_calls=getattr(args, "budget_max_llm_calls", 0),
        max_tokens=getattr(args, "budget_max_tokens", 0),
        max_time_seconds=getattr(args, "budget_max_time_seconds", 0),
        max_subprocess_calls=getattr(args, "budget_max_subprocess_calls", 0),
        warning_threshold=getattr(args, "budget_warning_threshold", 0.8),
    )
    
    events = EventConfig(
        enabled=getattr(args, "events_enabled", True),
        storage_path=getattr(args, "events_storage_path", ".rfsn/events.jsonl"),
        max_events_memory=getattr(args, "events_max_memory", 10000),
        max_events_storage=getattr(args, "events_max_storage", 100000),
        min_severity=getattr(args, "events_min_severity", "debug"),
        persist_events=getattr(args, "events_persist", True),
        include_subprocess=getattr(args, "events_include_subprocess", True),
        include_llm_calls=getattr(args, "events_include_llm", True),
        include_budget=getattr(args, "events_include_budget", True),
    )
    
    contracts = ContractConfig(
        enabled=getattr(args, "contracts_enabled", True),
        shell_execution_enabled=getattr(args, "contracts_shell_enabled", True),
        budget_tracking_enabled=getattr(args, "contracts_budget_enabled", True),
        llm_calling_enabled=getattr(args, "contracts_llm_enabled", True),
        event_logging_enabled=getattr(args, "contracts_events_enabled", True),
        strict_mode=getattr(args, "contracts_strict_mode", False),
        log_violations=getattr(args, "contracts_log_violations", True),
    )
    
    return ControllerConfig(
        repo_url=getattr(args, "repo", ""),
        repo_ref=getattr(args, "ref", None),
        feature_mode=getattr(args, "feature_mode", "repair"),
        test_command=getattr(args, "test", "pytest -q"),
        max_steps=getattr(args, "steps", 12),
        max_steps_without_progress=getattr(args, "max_steps_without_progress", 10),
        sandbox=sandbox,
        budget=budget,
        events=events,
        contracts=contracts,
        learning_db_path=getattr(args, "learning_db", None),
        policy_mode=getattr(args, "policy_mode", "off"),
        planner_mode=getattr(args, "planner_mode", "off"),
        repo_index_mode="on" if getattr(args, "repo_index", False) else "off",
        seed=getattr(args, "seed", 1337),
        model=getattr(args, "model", "deepseek-chat"),
        collect_finetuning_data=getattr(args, "collect_finetuning_data", False),
        parallel_patches=getattr(args, "parallel_patches", False),
        enable_llm_cache=getattr(args, "enable_llm_cache", False),
        no_eval=getattr(args, "no_eval", False),
    )
