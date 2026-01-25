"""Planner Layer v2.2 - High-level goal decomposition with advanced features.

This module provides a planner that sits ABOVE the controller and decomposes
high-level goals into structured, ordered plans. The planner:

- Translates goals into atomic, executable steps (LLM or pattern-based)
- Represents plans as explicit JSON artifacts
- Validates plans before execution (governance)
- Tracks resource budgets and halt conditions
- Records full audit trail for replay
- Supports parallel step execution
- Caches successful plans for reuse
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

# v2.2: LLM Decomposition
from .llm_decomposer import DecompositionConfig, DecompositionFallback, LLMDecomposer

# v2.2: Revision Strategies
from .revision_strategies import (
    BaseRevisionStrategy,
    CompileErrorRevision,
    ImportErrorRevision,
    RevisionResult,
    RevisionStrategyRegistry,
    ScopeReductionRevision,
    TestRegressionRevision,
    get_revision_registry,
)

# v2.2: QA Integration
from .qa_integration import PlannerQABridge, StepClaimGenerator, StepQAResult

# v2.2: Parallel Execution
from .parallel_executor import (
    ParallelBatch,
    ParallelExecutionConfig,
    ParallelResult,
    ParallelStepExecutor,
)

# v2.2: Plan Caching
from .plan_cache import CacheEntry, PlanCache

# v2.2: Metrics
from .metrics import MetricsCollector, PlannerMetrics, get_metrics_collector, reset_metrics

# v2.3: Tool Contract Registry
from .tool_registry import (
    ToolCategory,
    ToolContract,
    ToolContractRegistry,
    VerifyRecipe,
    get_tool_registry,
)

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
    # v2.2: LLM Decomposition
    "LLMDecomposer",
    "DecompositionConfig",
    "DecompositionFallback",
    # v2.2: Revision Strategies
    "BaseRevisionStrategy",
    "TestRegressionRevision",
    "CompileErrorRevision",
    "ImportErrorRevision",
    "ScopeReductionRevision",
    "RevisionStrategyRegistry",
    "RevisionResult",
    "get_revision_registry",
    # v2.2: QA Integration
    "PlannerQABridge",
    "StepQAResult",
    "StepClaimGenerator",
    # v2.2: Parallel Execution
    "ParallelStepExecutor",
    "ParallelBatch",
    "ParallelResult",
    "ParallelExecutionConfig",
    # v2.2: Plan Caching
    "PlanCache",
    "CacheEntry",
    # v2.2: Metrics
    "PlannerMetrics",
    "MetricsCollector",
    "get_metrics_collector",
    "reset_metrics",
    # v2.3: Tool Contract Registry
    "ToolCategory",
    "ToolContract",
    "ToolContractRegistry", 
    "VerifyRecipe",
    "get_tool_registry",
]


