"""Planner Layer v2.1 - High-level goal decomposition with governance.

This module provides a planner that sits ABOVE the controller and decomposes
high-level goals into structured, ordered plans. The planner:

- Translates goals into atomic, executable steps
- Represents plans as explicit JSON artifacts
- Validates plans before execution (governance)
- Tracks resource budgets and halt conditions
- Records full audit trail for replay
- Feeds the controller one step at a time
- NEVER executes code directly
- NEVER bypasses controller constraints

The controller remains the SOLE executor.

Example usage:
    from rfsn_controller.planner_v2 import PlannerV2, ControllerAdapter

    planner = PlannerV2()
    adapter = ControllerAdapter(planner)

    # Start a goal
    task_spec = adapter.start_goal("Fix failing test", {"test_cmd": "pytest"})

    # Execute in controller loop
    while task_spec:
        outcome = controller.execute(task_spec)
        task_spec = adapter.process_outcome(outcome)
"""

from .schema import (
    ControllerOutcome,
    ControllerTaskSpec,
    FailureCategory,
    FailureEvidence,
    Plan,
    PlanState,
    RiskLevel,
    Step,
    StepStatus,
)
from .lifecycle import StepLifecycle
from .planner import PlannerV2
from .memory_adapter import DecompositionPrior, MemoryAdapter
from .controller_adapter import ControllerAdapter

# Governance
from .governance import (
    BudgetExhausted,
    ContentSanitizer,
    HaltChecker,
    HaltSpec,
    PlanBudget,
    PlanValidator,
    RiskConstraints,
    SanitizationResult,
    ValidationError,
    ValidationResult,
    get_risk_constraints,
)

# Verification
from .verification_hooks import TestStrategy, VerificationHooks, VerificationType

# Artifacts and replay
from .artifact_log import PlanArtifact, PlanArtifactLog, StepArtifact
from .fingerprint import RepoFingerprint, compute_fingerprint
from .replay import PlanReplay, ReplayResult, StepDivergence

# CLI and overrides
from .cli import format_plan_for_logging, print_plan_dag, print_plan_summary, print_step_detail
from .overrides import OverrideManager, PlanOverride

__all__ = [
    # Schema
    "Step",
    "Plan",
    "PlanState",
    "StepStatus",
    "RiskLevel",
    "ControllerTaskSpec",
    "ControllerOutcome",
    "FailureCategory",
    "FailureEvidence",
    # Lifecycle
    "StepLifecycle",
    # Planner
    "PlannerV2",
    # Memory
    "MemoryAdapter",
    "DecompositionPrior",
    # Adapter
    "ControllerAdapter",
    # Governance
    "PlanValidator",
    "ValidationResult",
    "ValidationError",
    "PlanBudget",
    "BudgetExhausted",
    "RiskConstraints",
    "get_risk_constraints",
    "HaltSpec",
    "HaltChecker",
    "ContentSanitizer",
    "SanitizationResult",
    # Verification
    "VerificationHooks",
    "VerificationType",
    "TestStrategy",
    # Artifacts
    "PlanArtifact",
    "PlanArtifactLog",
    "StepArtifact",
    "RepoFingerprint",
    "compute_fingerprint",
    # Replay
    "PlanReplay",
    "ReplayResult",
    "StepDivergence",
    # CLI
    "print_plan_dag",
    "print_plan_summary",
    "print_step_detail",
    "format_plan_for_logging",
    # Overrides
    "PlanOverride",
    "OverrideManager",
]

