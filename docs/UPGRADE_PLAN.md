# RFSN Controller Upgrade Plan: Stages 3-5

## Document Version
- **Version**: 1.0
- **Created**: 2026-01-20
- **Last Updated**: 2026-01-20
- **Status**: Draft

---

## 1. Executive Summary

### Overview of Remaining Work

This document outlines the comprehensive implementation plan for completing the RFSN Controller upgrade from the current state (Stages 1-2 complete) through final production readiness (Stage 5).

| Stage | Phases/Versions | Focus Area | Estimated Effort |
|-------|-----------------|------------|------------------|
| Stage 3 | Phases 6-7 | Planning & Optimization | 4-6 weeks |
| Stage 4 | Phases 8-10 | Memory & Artifacts | 5-7 weeks |
| Stage 5 | v2-v10 | Advanced Features | 16-24 weeks |

### Current State (Completed)

| Stage | Status | Tests | Coverage |
|-------|--------|-------|----------|
| Stage 1 (Phases 1-3) | ✅ Complete | 492 | ~93% |
| Stage 2 (Phases 4-5) | ✅ Complete | 126 | ~95% |
| **Total** | **Complete** | **618+** | **~90%** |

**Completed Capabilities:**
- Shell elimination with secure subprocess execution
- Comprehensive testing infrastructure
- Budget gates and resource tracking
- Structured event logging system
- Feature contract enforcement

### Strategic Priorities

1. **Budget-Aware Planning** (Phase 6) - Enable cost-conscious decision making
2. **Performance Optimization** (Phase 7) - Improve execution efficiency
3. **Learning & Memory** (Phase 8) - Leverage historical outcomes
4. **Production Readiness** (Phases 9-10) - Stable CLI and artifact management
5. **Enterprise Features** (v2-v10) - Multi-tenant, governance, HITL operations

### Resource Requirements

| Resource | Estimate |
|----------|----------|
| Senior Engineers | 2-3 FTE |
| QA/Test Engineers | 1 FTE |
| DevOps | 0.5 FTE (Stage 5) |
| Total Duration | 25-37 weeks |

### Timeline Estimates

```
2026-Q1: Stage 3 (Phases 6-7) - Planning & Optimization
2026-Q2: Stage 4 (Phases 8-10) - Memory & Artifacts  
2026-Q2-Q4: Stage 5 (v2-v10) - Advanced Features
```

---

## 2. Stage 3: Planning & Optimization (Phases 6-7)

### Phase 6: Planner Budget Tracking

#### 6.1 Overview

Integrate budget awareness into the DAG-based planner to enable cost-conscious planning decisions and real-time budget monitoring during execution.

**Goals:**
- Cost estimation before plan execution
- Budget constraints in plan generation
- Real-time budget monitoring during execution
- Plan adaptation when budget thresholds are reached

#### 6.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Budget-Aware Planner                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Cost       │    │   Budget     │    │   Plan        │  │
│  │  Estimator  │───▶│   Optimizer  │───▶│   Executor    │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Historical │    │   Budget     │    │   Budget      │  │
│  │  Metrics    │    │   Monitor    │    │   Events      │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

##### Cost Estimator Component

```python
@dataclass
class CostEstimate:
    """Estimated resource cost for a plan node or action."""
    
    estimated_llm_calls: int = 0
    estimated_tokens: int = 0
    estimated_subprocess_calls: int = 0
    estimated_time_seconds: float = 0.0
    confidence: float = 0.8  # 0.0-1.0 confidence in estimate
    
    def total_cost(self, weights: Optional[CostWeights] = None) -> float:
        """Calculate weighted total cost."""
        ...

class CostEstimator:
    """Estimates resource costs for plan nodes."""
    
    def __init__(self, historical_data: Optional[ActionMemory] = None):
        self.historical_data = historical_data
        self._action_cost_cache: Dict[str, CostEstimate] = {}
    
    def estimate_node_cost(self, node: PlanNode) -> CostEstimate:
        """Estimate cost for a single plan node."""
        ...
    
    def estimate_plan_cost(self, dag: PlanDAG) -> CostEstimate:
        """Estimate total cost for entire plan."""
        ...
    
    def estimate_action_cost(self, action_type: str, action_params: Dict) -> CostEstimate:
        """Estimate cost for a specific action."""
        ...
```

##### Budget Optimizer Component

```python
class BudgetOptimizer:
    """Optimizes plans to fit within budget constraints."""
    
    def __init__(self, budget: Budget, estimator: CostEstimator):
        self.budget = budget
        self.estimator = estimator
    
    def optimize_plan(self, dag: PlanDAG) -> PlanDAG:
        """Optimize plan to fit budget constraints."""
        ...
    
    def can_execute_node(self, node: PlanNode) -> Tuple[bool, str]:
        """Check if node can be executed within remaining budget."""
        ...
    
    def suggest_alternatives(self, node: PlanNode) -> List[PlanNode]:
        """Suggest cheaper alternative nodes when budget is tight."""
        ...
```

#### 6.3 Implementation Details

##### New Files

| File | Description | Lines (Est.) |
|------|-------------|--------------|
| `rfsn_controller/cost_estimator.py` | Cost estimation logic | ~400 |
| `rfsn_controller/budget_optimizer.py` | Budget-aware optimization | ~350 |
| `tests/test_cost_estimator.py` | Cost estimator tests | ~500 |
| `tests/test_budget_optimizer.py` | Budget optimizer tests | ~400 |

##### Modified Files

| File | Changes |
|------|---------|
| `planner.py` | Add budget integration hooks, cost estimation calls |
| `budget.py` | Add projection/reservation methods |
| `controller.py` | Initialize budget-aware planner |
| `config.py` | Add BudgetPlannerConfig |
| `context.py` | Add cost_estimator property |

##### Key Implementation Steps

1. **Cost Estimation System**
   ```python
   # planner.py additions
   
   class BudgetAwarePlanner(Planner):
       """Extended planner with budget awareness."""
       
       def __init__(self, ctx: ControllerContext, budget: Budget):
           super().__init__(ctx)
           self.budget = budget
           self.cost_estimator = CostEstimator(ctx.action_memory)
           self.budget_optimizer = BudgetOptimizer(budget, self.cost_estimator)
       
       def generate_plan(self, problem: str, constraints: PlanConstraints) -> PlanDAG:
           """Generate budget-aware plan."""
           # Generate initial plan
           dag = super().generate_plan(problem, constraints)
           
           # Estimate costs
           total_cost = self.cost_estimator.estimate_plan_cost(dag)
           
           # Check against budget
           remaining = self.budget.get_remaining()
           if not self._fits_budget(total_cost, remaining):
               dag = self.budget_optimizer.optimize_plan(dag)
           
           return dag
   ```

2. **Budget Projection API**
   ```python
   # budget.py additions
   
   def get_remaining(self) -> BudgetRemaining:
       """Get remaining budget for all resources."""
       return BudgetRemaining(
           steps=self.max_steps - self._consumed_steps,
           llm_calls=self.max_llm_calls - self._consumed_llm_calls,
           tokens=self.max_tokens - self._consumed_tokens,
           time_seconds=self.max_time_seconds - self._elapsed_time(),
           subprocess_calls=self.max_subprocess_calls - self._consumed_subprocess_calls,
       )
   
   def reserve(self, estimate: CostEstimate) -> BudgetReservation:
       """Reserve budget for planned operation."""
       ...
   
   def release_reservation(self, reservation: BudgetReservation) -> None:
       """Release unused reservation."""
       ...
   ```

3. **Execution Monitoring**
   ```python
   # planner.py additions
   
   def execute_node_with_budget(self, node: PlanNode) -> NodeResult:
       """Execute node with budget monitoring."""
       # Check if we can proceed
       can_execute, reason = self.budget_optimizer.can_execute_node(node)
       if not can_execute:
           log_budget_warning_global("node_blocked", node.id, reason)
           return NodeResult(status=NodeStatus.SKIPPED, reason=reason)
       
       # Reserve estimated budget
       estimate = self.cost_estimator.estimate_node_cost(node)
       reservation = self.budget.reserve(estimate)
       
       try:
           result = self.execute_node(node)
           return result
       finally:
           self.budget.release_reservation(reservation)
   ```

#### 6.4 Integration Points

| Component | Integration |
|-----------|-------------|
| `planner.py` | Core budget-aware planning logic |
| `budget.py` | Reservation/projection APIs |
| `controller.py` | Initialize budget-aware planner |
| `config.py` | `BudgetPlannerConfig` dataclass |
| `context.py` | `cost_estimator` property |
| `events.py` | Budget estimation events |

#### 6.5 Testing Strategy

**Unit Tests (60+ tests)**
- Cost estimator accuracy
- Budget optimizer algorithms
- Reservation lifecycle
- Edge cases (zero budget, unlimited budget)

**Integration Tests (20+ tests)**
- End-to-end budget-aware planning
- Plan adaptation under constraints
- Event logging verification

**Performance Tests**
- Cost estimation overhead < 10ms
- Plan optimization < 100ms

#### 6.6 Estimated Effort

| Task | Duration |
|------|----------|
| Design & architecture | 3 days |
| Cost estimator implementation | 5 days |
| Budget optimizer implementation | 5 days |
| Planner integration | 3 days |
| Testing | 5 days |
| Documentation | 2 days |
| **Total** | **~23 days (4-5 weeks)** |

---

### Phase 7: Nonlinear Optimizer Module

#### 7.1 Overview

Implement a nonlinear optimization module for parameter tuning, resource allocation, and adaptive planning using numerical optimization techniques.

**Goals:**
- Optimize planner parameters dynamically
- Resource allocation across parallel operations
- Adaptive threshold tuning based on performance
- Integration with scipy/numpy optimization

#### 7.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Nonlinear Optimizer                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Objective  │    │   Constraint │    │    Solver     │  │
│  │  Functions  │───▶│   Manager    │───▶│   Interface   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Parameter  │    │   Solution   │    │   Result      │  │
│  │  Space      │    │   Cache      │    │   Validator   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 7.3 Core Components

##### Objective Functions

```python
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np

class ObjectiveFunction(ABC):
    """Base class for optimization objectives."""
    
    @abstractmethod
    def evaluate(self, params: np.ndarray) -> float:
        """Evaluate objective function at params."""
        ...
    
    @abstractmethod
    def gradient(self, params: np.ndarray) -> np.ndarray:
        """Compute gradient at params (if available)."""
        ...
    
    @property
    @abstractmethod
    def bounds(self) -> List[Tuple[float, float]]:
        """Parameter bounds [(lower, upper), ...]."""
        ...


class BudgetAllocationObjective(ObjectiveFunction):
    """Optimize budget allocation across plan nodes."""
    
    def __init__(self, nodes: List[PlanNode], total_budget: Budget):
        self.nodes = nodes
        self.total_budget = total_budget
    
    def evaluate(self, allocation: np.ndarray) -> float:
        """Minimize expected total cost while maximizing success probability."""
        ...


class ParameterTuningObjective(ObjectiveFunction):
    """Optimize controller parameters based on historical performance."""
    
    def __init__(self, historical_data: List[RunMetrics], param_names: List[str]):
        self.historical_data = historical_data
        self.param_names = param_names
    
    def evaluate(self, params: np.ndarray) -> float:
        """Maximize expected success rate given parameters."""
        ...
```

##### Constraint System

```python
@dataclass
class OptimizationConstraint:
    """A constraint for the optimization problem."""
    
    name: str
    type: str  # 'eq' for equality, 'ineq' for inequality
    func: Callable[[np.ndarray], float]
    jac: Optional[Callable[[np.ndarray], np.ndarray]] = None


class ConstraintManager:
    """Manages constraints for optimization problems."""
    
    def __init__(self):
        self._constraints: List[OptimizationConstraint] = []
    
    def add_constraint(self, constraint: OptimizationConstraint) -> None:
        """Add a constraint."""
        ...
    
    def add_budget_constraint(self, budget: Budget) -> None:
        """Add budget-based constraints."""
        ...
    
    def add_time_constraint(self, max_seconds: float) -> None:
        """Add time constraint."""
        ...
    
    def to_scipy_constraints(self) -> List[Dict]:
        """Convert to scipy.optimize constraint format."""
        ...
```

##### Solver Interface

```python
from enum import Enum
from scipy.optimize import minimize, differential_evolution, basinhopping

class SolverType(Enum):
    """Available optimization solvers."""
    
    SLSQP = "slsqp"           # Sequential Least Squares Programming
    L_BFGS_B = "l-bfgs-b"     # Limited-memory BFGS with bounds
    DIFF_EVOLUTION = "de"     # Differential Evolution (global)
    BASIN_HOPPING = "bh"      # Basin Hopping (global)
    NELDER_MEAD = "nm"        # Simplex (gradient-free)


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    
    success: bool
    optimal_params: np.ndarray
    optimal_value: float
    iterations: int
    func_evaluations: int
    message: str
    solver_used: SolverType


class NonlinearOptimizer:
    """Main optimizer class with multiple solver backends."""
    
    def __init__(
        self,
        objective: ObjectiveFunction,
        constraints: Optional[ConstraintManager] = None,
        solver: SolverType = SolverType.SLSQP,
    ):
        self.objective = objective
        self.constraints = constraints or ConstraintManager()
        self.solver = solver
        self._cache: Dict[bytes, float] = {}
    
    def optimize(
        self,
        initial_guess: Optional[np.ndarray] = None,
        max_iterations: int = 1000,
        tolerance: float = 1e-6,
    ) -> OptimizationResult:
        """Run optimization."""
        ...
    
    def optimize_with_restarts(
        self,
        n_restarts: int = 5,
        **kwargs,
    ) -> OptimizationResult:
        """Run optimization with multiple random restarts."""
        ...
```

#### 7.4 Use Cases

##### 1. Budget Allocation Optimization

```python
# Allocate budget across plan nodes to maximize success probability
optimizer = NonlinearOptimizer(
    objective=BudgetAllocationObjective(nodes, budget),
    constraints=ConstraintManager().add_budget_constraint(budget),
    solver=SolverType.SLSQP,
)

result = optimizer.optimize()
allocations = result.optimal_params
```

##### 2. Parameter Tuning

```python
# Optimize controller parameters based on historical performance
optimizer = NonlinearOptimizer(
    objective=ParameterTuningObjective(history, ["retry_delay", "timeout_factor"]),
    solver=SolverType.L_BFGS_B,
)

result = optimizer.optimize()
optimal_config = dict(zip(param_names, result.optimal_params))
```

##### 3. Resource Scheduling

```python
# Schedule parallel operations to minimize makespan
optimizer = NonlinearOptimizer(
    objective=MakespanObjective(operations, resources),
    constraints=ConstraintManager().add_resource_constraints(resources),
    solver=SolverType.DIFF_EVOLUTION,
)
```

#### 7.5 Implementation Details

##### New Files

| File | Description | Lines (Est.) |
|------|-------------|--------------|
| `rfsn_controller/optimizer.py` | Core optimizer module | ~600 |
| `rfsn_controller/objectives.py` | Objective function library | ~400 |
| `rfsn_controller/constraints.py` | Constraint system | ~300 |
| `tests/test_optimizer.py` | Optimizer tests | ~600 |
| `tests/test_objectives.py` | Objective function tests | ~400 |

##### Modified Files

| File | Changes |
|------|---------|
| `planner.py` | Add optimizer integration |
| `config.py` | Add `OptimizerConfig` |
| `context.py` | Add `optimizer` property |
| `requirements.txt` | Add scipy dependency |

#### 7.6 Integration Points

| Component | Integration |
|-----------|-------------|
| `planner.py` | Budget allocation optimization |
| `controller.py` | Parameter tuning |
| `config.py` | `OptimizerConfig` dataclass |
| `budget_optimizer.py` | Cost minimization |
| `parallel.py` | Resource scheduling |

#### 7.7 Testing Strategy

**Unit Tests (80+ tests)**
- Objective function correctness
- Constraint satisfaction
- Solver convergence
- Edge cases (infeasible, unbounded)

**Integration Tests (30+ tests)**
- End-to-end optimization workflows
- Parameter tuning accuracy
- Budget allocation effectiveness

**Benchmarks**
- Solver performance comparison
- Scalability with problem size

#### 7.8 Estimated Effort

| Task | Duration |
|------|----------|
| Design & architecture | 2 days |
| Core optimizer implementation | 5 days |
| Objective function library | 4 days |
| Constraint system | 3 days |
| Integration with planner | 3 days |
| Testing | 5 days |
| Documentation | 2 days |
| **Total** | **~24 days (4-5 weeks)** |

---

## 3. Stage 4: Memory & Artifacts (Phases 8-10)

### Phase 8: Action-Outcome Metrics Memory

#### 8.1 Overview

Enhance the existing `action_outcome_memory.py` module with comprehensive metrics tracking, analysis capabilities, and integration with the planning system.

**Goals:**
- Persistent storage of action outcomes
- Statistical analysis of action effectiveness
- Learning-based action selection
- Performance trend tracking

#### 8.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Action-Outcome Memory System                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   Outcome   │    │   Metrics    │    │   Learning    │  │
│  │   Recorder  │───▶│   Analyzer   │───▶│   Engine      │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   SQLite    │    │   Trend      │    │   Prior       │  │
│  │   Storage   │    │   Detector   │    │   Generator   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 8.3 Enhanced Components

```python
@dataclass
class ActionOutcome:
    """Complete outcome record for an action."""
    
    id: str
    timestamp: datetime
    context: ContextSignature
    action_type: str
    action_params: Dict[str, Any]
    outcome: str  # success, partial, failure
    metrics: OutcomeMetrics
    feedback: Optional[str] = None


@dataclass 
class OutcomeMetrics:
    """Detailed metrics for an action outcome."""
    
    exec_time_ms: int
    command_count: int
    diff_lines: int
    regressions: int
    tests_fixed: int
    tests_broken: int
    llm_calls: int
    tokens_used: int
    retries: int


class ActionMemoryStore:
    """Enhanced SQLite-based action outcome storage."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = self._init_db()
    
    def record_outcome(self, outcome: ActionOutcome) -> str:
        """Record an action outcome."""
        ...
    
    def get_similar_outcomes(
        self,
        context: ContextSignature,
        action_type: str,
        limit: int = 10,
    ) -> List[ActionOutcome]:
        """Get outcomes for similar contexts."""
        ...
    
    def get_success_rate(
        self,
        action_type: str,
        context_filter: Optional[Dict] = None,
    ) -> float:
        """Calculate success rate for action type."""
        ...


class MetricsAnalyzer:
    """Analyzes action metrics for insights."""
    
    def __init__(self, store: ActionMemoryStore):
        self.store = store
    
    def get_action_effectiveness(self, action_type: str) -> EffectivenessReport:
        """Analyze effectiveness of an action type."""
        ...
    
    def detect_performance_trends(
        self,
        window_days: int = 7,
    ) -> List[PerformanceTrend]:
        """Detect performance trends over time."""
        ...
    
    def recommend_actions(
        self,
        context: ContextSignature,
        k: int = 5,
    ) -> List[ActionRecommendation]:
        """Recommend actions based on historical success."""
        ...
```

#### 8.4 Database Schema

```sql
-- Enhanced schema for action outcomes

CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    context_hash TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_key TEXT NOT NULL,
    action_json TEXT NOT NULL,
    outcome TEXT NOT NULL,
    score REAL NOT NULL,
    
    -- Metrics
    exec_time_ms INTEGER,
    command_count INTEGER,
    diff_lines INTEGER,
    regressions INTEGER,
    tests_fixed INTEGER,
    tests_broken INTEGER,
    llm_calls INTEGER,
    tokens_used INTEGER,
    retries INTEGER,
    
    -- Indexes
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcomes_context ON outcomes(context_hash);
CREATE INDEX IF NOT EXISTS idx_outcomes_action_type ON outcomes(action_type);
CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp ON outcomes(timestamp);

CREATE TABLE IF NOT EXISTS action_priors (
    context_hash TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_key TEXT NOT NULL,
    weight REAL NOT NULL,
    success_rate REAL NOT NULL,
    mean_score REAL NOT NULL,
    n INTEGER NOT NULL,
    last_updated TEXT NOT NULL,
    PRIMARY KEY (context_hash, action_type, action_key)
);

CREATE TABLE IF NOT EXISTS performance_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    trend_direction TEXT NOT NULL,  -- improving, degrading, stable
    trend_value REAL NOT NULL,
    confidence REAL NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### 8.5 Integration Points

| Component | Integration |
|-----------|-------------|
| `planner.py` | Action recommendation |
| `controller.py` | Outcome recording |
| `policy.py` | Policy decision enhancement |
| `cost_estimator.py` | Historical cost data |
| `events.py` | Outcome events |

#### 8.6 Estimated Effort

| Task | Duration |
|------|----------|
| Schema enhancement | 2 days |
| Store implementation | 4 days |
| Metrics analyzer | 4 days |
| Integration | 3 days |
| Testing | 4 days |
| Documentation | 1 day |
| **Total** | **~18 days (3-4 weeks)** |

---

### Phase 9: Stable CLI Entrypoint

#### 9.1 Overview

Create a production-ready CLI with stable interfaces, comprehensive argument parsing, configuration validation, and proper error handling.

**Goals:**
- Stable, documented CLI interface
- Configuration file support
- Proper exit codes and error messages
- Shell completion support
- Version management

#### 9.2 CLI Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RFSN CLI                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  rfsn                                                        │
│  ├── run         # Execute controller on repo                │
│  ├── plan        # Generate execution plan only              │
│  ├── verify      # Verify changes without applying           │
│  ├── config      # Configuration management                  │
│  │   ├── show    # Show current config                       │
│  │   ├── validate # Validate config file                     │
│  │   └── init    # Initialize config file                    │
│  ├── memory      # Action memory management                  │
│  │   ├── stats   # Show memory statistics                    │
│  │   ├── export  # Export memory data                        │
│  │   └── prune   # Prune old entries                        │
│  └── version     # Show version info                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 9.3 Implementation

```python
# cli.py - Refactored with Click

import click
from typing import Optional

@click.group()
@click.version_option(version=__version__)
@click.option('--config', '-c', type=click.Path(), help='Config file path')
@click.option('--verbose', '-v', count=True, help='Increase verbosity')
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], verbose: int) -> None:
    """RFSN Controller - Autonomous code repair agent."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config) if config else get_default_config()
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument('repo')
@click.option('--test', '-t', default='pytest -q', help='Test command')
@click.option('--ref', help='Git ref to checkout')
@click.option('--steps', type=int, default=12, help='Max steps')
@click.option('--budget-llm-calls', type=int, help='Max LLM calls')
@click.option('--budget-tokens', type=int, help='Max tokens')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.pass_context
def run(ctx: click.Context, repo: str, **kwargs) -> None:
    """Run controller on a repository."""
    ...


@cli.command()
@click.argument('repo')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def plan(ctx: click.Context, repo: str, output: Optional[str]) -> None:
    """Generate execution plan without running."""
    ...


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command('init')
@click.option('--output', '-o', default='.rfsn.yaml', help='Output path')
def config_init(output: str) -> None:
    """Initialize a configuration file."""
    ...
```

#### 9.4 Configuration File Format

```yaml
# .rfsn.yaml - RFSN Controller Configuration

version: "1.0"

# Execution settings
execution:
  max_steps: 12
  max_minutes: 30
  fix_all: false
  model: deepseek-chat

# Budget limits
budget:
  max_llm_calls: 100
  max_tokens: 500000
  max_subprocess_calls: 200
  warning_threshold: 0.8

# Contract enforcement
contracts:
  enable_shell_contract: true
  enable_budget_contract: true
  enable_llm_contract: true
  strict_mode: false

# Event logging
events:
  enabled: true
  output_dir: .rfsn/events
  max_events: 10000

# Memory settings
memory:
  enabled: true
  db_path: .rfsn/memory.db
  prune_days: 30
```

#### 9.5 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all tests pass |
| 1 | Failure - tests still failing |
| 2 | Budget exceeded |
| 3 | Configuration error |
| 4 | Repository error |
| 5 | Network error |
| 10 | Internal error |

#### 9.6 Estimated Effort

| Task | Duration |
|------|----------|
| CLI refactoring with Click | 3 days |
| Configuration system | 2 days |
| Subcommands implementation | 3 days |
| Error handling | 2 days |
| Shell completion | 1 day |
| Testing | 3 days |
| Documentation | 2 days |
| **Total** | **~16 days (3 weeks)** |

---

### Phase 10: Run Artifact Model

#### 10.1 Overview

Implement a comprehensive artifact model for capturing, storing, and analyzing run outputs including patches, logs, metrics, and evidence.

**Goals:**
- Structured run artifacts
- Reproducible run capture
- Evidence collection for verification
- Export formats (JSON, SARIF, HTML)

#### 10.2 Artifact Model

```python
@dataclass
class RunArtifact:
    """Complete artifact from a controller run."""
    
    # Identification
    run_id: str
    timestamp: datetime
    version: str
    
    # Input
    repo_url: str
    repo_ref: Optional[str]
    test_command: str
    config: ControllerConfig
    
    # Execution
    plan: PlanDAG
    steps: List[StepArtifact]
    events: List[Event]
    
    # Output
    patches: List[PatchArtifact]
    final_state: FinalState
    
    # Metrics
    metrics: RunMetrics
    budget_usage: BudgetUsage


@dataclass
class StepArtifact:
    """Artifact for a single execution step."""
    
    step_number: int
    node_id: str
    action: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    duration_ms: int
    llm_calls: List[LLMCallArtifact]
    commands: List[CommandArtifact]


@dataclass
class PatchArtifact:
    """A generated patch with metadata."""
    
    file_path: str
    diff: str
    hunks: List[DiffHunk]
    applied: bool
    verified: bool
    tests_fixed: int
    tests_broken: int


class ArtifactStore:
    """Persistent storage for run artifacts."""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
    
    def save_run(self, artifact: RunArtifact) -> str:
        """Save run artifact, return artifact path."""
        ...
    
    def load_run(self, run_id: str) -> RunArtifact:
        """Load a run artifact by ID."""
        ...
    
    def list_runs(
        self,
        repo_filter: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[RunSummary]:
        """List available run artifacts."""
        ...
    
    def export_sarif(self, run_id: str, output_path: str) -> None:
        """Export run as SARIF format."""
        ...
    
    def export_html(self, run_id: str, output_path: str) -> None:
        """Export run as HTML report."""
        ...
```

#### 10.3 Directory Structure

```
.rfsn/
├── artifacts/
│   ├── runs/
│   │   ├── run_20260120_123456_abc123/
│   │   │   ├── metadata.json
│   │   │   ├── plan.json
│   │   │   ├── steps/
│   │   │   │   ├── step_001.json
│   │   │   │   └── step_002.json
│   │   │   ├── patches/
│   │   │   │   ├── patch_001.diff
│   │   │   │   └── patch_002.diff
│   │   │   ├── events.jsonl
│   │   │   └── metrics.json
│   │   └── index.json
├── memory.db
└── config.yaml
```

#### 10.4 Estimated Effort

| Task | Duration |
|------|----------|
| Artifact model design | 2 days |
| Storage implementation | 4 days |
| Export formats (SARIF, HTML) | 4 days |
| Integration | 3 days |
| Testing | 3 days |
| Documentation | 1 day |
| **Total** | **~17 days (3-4 weeks)** |

---

## 4. Stage 5: Advanced Features (v2-v10)

### v2: Controller Attestation & Promotion Gates

#### 4.1.1 Overview

Implement cryptographic attestation of controller runs and promotion gates for controlled deployment of fixes.

**Features:**
- Signed run attestations
- Promotion gate policies
- Approval workflows
- Audit trail

#### 4.1.2 Architecture

```python
@dataclass
class Attestation:
    """Cryptographically signed attestation of a controller run."""
    
    run_id: str
    timestamp: datetime
    subject: AttestationSubject
    predicate: AttestationPredicate
    signature: str


class PromotionGate:
    """Gate that must pass before promoting a fix."""
    
    name: str
    conditions: List[GateCondition]
    approvers: List[str]
    
    def evaluate(self, artifact: RunArtifact) -> GateResult:
        """Evaluate if gate passes."""
        ...


class PromotionPipeline:
    """Pipeline of promotion gates."""
    
    def __init__(self, gates: List[PromotionGate]):
        self.gates = gates
    
    def evaluate(self, artifact: RunArtifact) -> PipelineResult:
        """Evaluate all gates."""
        ...
    
    def promote(self, artifact: RunArtifact, approvals: List[Approval]) -> None:
        """Promote artifact through pipeline."""
        ...
```

#### 4.1.3 Estimated Effort: 2-3 weeks

---

### v3: Policy Versioning & Patch Apply Bot

#### 4.2.1 Overview

Implement versioned policies and an automated patch application bot.

**Features:**
- Policy version control
- Policy migration
- Automated patch application
- GitHub/GitLab integration

#### 4.2.2 Components

```python
@dataclass
class PolicyVersion:
    """A versioned policy definition."""
    
    version: str
    rules: List[PolicyRule]
    effective_from: datetime
    deprecated_at: Optional[datetime]


class PatchApplyBot:
    """Bot for automated patch application."""
    
    def __init__(self, git_provider: GitProvider):
        self.git_provider = git_provider
    
    async def create_pr(
        self,
        artifact: RunArtifact,
        target_branch: str,
    ) -> PullRequest:
        """Create PR with patches."""
        ...
    
    async def auto_merge(
        self,
        pr: PullRequest,
        conditions: MergeConditions,
    ) -> MergeResult:
        """Auto-merge PR if conditions met."""
        ...
```

#### 4.2.3 Estimated Effort: 2-3 weeks

---

### v4: SARIF Output & Dependency Governance

#### 4.3.1 Overview

Implement SARIF output for integration with code scanning tools and dependency governance for secure dependency management.

**Features:**
- SARIF 2.1.0 output format
- Integration with GitHub Code Scanning
- Dependency vulnerability tracking
- License compliance checking

#### 4.3.2 SARIF Integration

```python
class SARIFExporter:
    """Export run results as SARIF format."""
    
    SARIF_VERSION = "2.1.0"
    SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
    
    def export(self, artifact: RunArtifact) -> Dict:
        """Export artifact as SARIF document."""
        return {
            "$schema": self.SCHEMA_URI,
            "version": self.SARIF_VERSION,
            "runs": [self._build_run(artifact)],
        }
    
    def _build_run(self, artifact: RunArtifact) -> Dict:
        """Build SARIF run object."""
        ...


class DependencyGovernor:
    """Govern dependency updates and security."""
    
    def scan_dependencies(self, repo_path: str) -> DependencyScanResult:
        """Scan repository dependencies."""
        ...
    
    def check_vulnerabilities(self, deps: List[Dependency]) -> List[Vulnerability]:
        """Check for known vulnerabilities."""
        ...
    
    def check_licenses(self, deps: List[Dependency]) -> List[LicenseIssue]:
        """Check for license compliance."""
        ...
```

#### 4.3.3 Estimated Effort: 2 weeks

---

### v5: Two-Person Policy Control

#### 4.4.1 Overview

Implement two-person control for sensitive operations requiring dual approval.

**Features:**
- Dual approval requirements
- Separation of duties
- Approval workflows
- Audit logging

```python
class TwoPersonControl:
    """Enforce two-person control for sensitive operations."""
    
    def __init__(self, policy: TwoPersonPolicy):
        self.policy = policy
    
    def request_approval(
        self,
        operation: SensitiveOperation,
        requestor: str,
    ) -> ApprovalRequest:
        """Request approval for sensitive operation."""
        ...
    
    def approve(
        self,
        request: ApprovalRequest,
        approver: str,
    ) -> ApprovalResult:
        """Approve request (must be different from requestor)."""
        ...
```

#### 4.4.2 Estimated Effort: 1-2 weeks

---

### v6: Worker Services & Multi-Tenant Isolation

#### 4.5.1 Overview

Implement worker services for distributed execution and multi-tenant isolation.

**Features:**
- Background worker services
- Job queuing (Redis/RabbitMQ)
- Tenant isolation
- Resource quotas per tenant

#### 4.5.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────┐    ┌───────────┐    ┌───────────────────┐   │
│  │  Tenant A │    │  Tenant B │    │     Tenant C      │   │
│  └─────┬─────┘    └─────┬─────┘    └─────────┬─────────┘   │
│        │                │                    │              │
│        ▼                ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    API Gateway                       │   │
│  │            (Authentication, Rate Limiting)           │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                │
│                            ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Job Queue                         │   │
│  │              (Redis / RabbitMQ)                      │   │
│  └───────────┬─────────────┬─────────────┬─────────────┘   │
│              │             │             │                  │
│              ▼             ▼             ▼                  │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     │
│  │   Worker 1    │ │   Worker 2    │ │   Worker 3    │     │
│  │  (Isolated)   │ │  (Isolated)   │ │  (Isolated)   │     │
│  └───────────────┘ └───────────────┘ └───────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 4.5.3 Estimated Effort: 3-4 weeks

---

### v7: Distributed Runners

#### 4.6.1 Overview

Implement distributed runner infrastructure for horizontal scaling.

**Features:**
- Runner registration/discovery
- Load balancing
- Failover handling
- Runner health monitoring

```python
class DistributedRunner:
    """Distributed runner with coordination."""
    
    def __init__(self, coordinator: Coordinator):
        self.coordinator = coordinator
        self.runner_id = self._generate_runner_id()
    
    async def register(self) -> None:
        """Register runner with coordinator."""
        ...
    
    async def claim_job(self) -> Optional[Job]:
        """Claim next available job."""
        ...
    
    async def report_health(self) -> None:
        """Report health status."""
        ...


class Coordinator:
    """Coordinates distributed runners."""
    
    def __init__(self, backend: CoordinatorBackend):
        self.backend = backend
    
    async def assign_job(self, job: Job) -> str:
        """Assign job to best available runner."""
        ...
    
    async def handle_failure(self, runner_id: str, job_id: str) -> None:
        """Handle runner failure, reassign job."""
        ...
```

#### 4.6.2 Estimated Effort: 3-4 weeks

---

### v8: Policy-Aware Learning

#### 4.7.1 Overview

Implement learning systems that respect policy constraints.

**Features:**
- Policy-constrained learning
- Safe exploration
- Reward shaping from policy
- Policy compliance metrics

```python
class PolicyAwareLearner:
    """Learning system that respects policy constraints."""
    
    def __init__(self, policy: Policy, memory: ActionMemoryStore):
        self.policy = policy
        self.memory = memory
    
    def learn_from_outcomes(self, outcomes: List[ActionOutcome]) -> None:
        """Learn from outcomes while respecting policy."""
        ...
    
    def suggest_action(
        self,
        context: ContextSignature,
        constraints: List[PolicyConstraint],
    ) -> ActionSuggestion:
        """Suggest policy-compliant action."""
        ...
```

#### 4.7.2 Estimated Effort: 2-3 weeks

---

### v9: Human-in-the-Loop (HITL) Operations

#### 4.8.1 Overview

Implement HITL workflows for human oversight and intervention.

**Features:**
- Breakpoint system
- Human review requests
- Approval workflows
- Interactive debugging

```python
class HITLController:
    """Human-in-the-loop controller extension."""
    
    def __init__(self, base_controller: Controller, ui: HITLInterface):
        self.base_controller = base_controller
        self.ui = ui
    
    async def run_with_hitl(self, config: ControllerConfig) -> RunResult:
        """Run controller with HITL checkpoints."""
        ...
    
    async def request_review(
        self,
        checkpoint: Checkpoint,
        context: ReviewContext,
    ) -> ReviewDecision:
        """Request human review at checkpoint."""
        ...
    
    async def handle_intervention(
        self,
        intervention: HumanIntervention,
    ) -> None:
        """Handle human intervention."""
        ...
```

#### 4.8.2 Estimated Effort: 3-4 weeks

---

### v10: Developer UX Polish

#### 4.9.1 Overview

Final polish for developer experience including IDE integration, better error messages, and comprehensive documentation.

**Features:**
- VS Code extension
- Rich error messages
- Progress indicators
- Interactive tutorials
- API documentation

#### 4.9.2 Deliverables

| Deliverable | Description |
|-------------|-------------|
| VS Code Extension | Run RFSN from IDE |
| Error Catalog | Comprehensive error documentation |
| CLI Improvements | Progress bars, colors, interactive mode |
| Documentation Site | Full API docs, tutorials, examples |
| Telemetry Dashboard | Optional telemetry visualization |

#### 4.9.3 Estimated Effort: 2-3 weeks

---

## 5. Technical Specifications

### 5.1 API Designs

#### Cost Estimation API

```python
# POST /api/v1/estimate
{
    "plan": {...},  # PlanDAG JSON
    "budget": {...},  # Current budget state
}

# Response
{
    "estimated_cost": {
        "llm_calls": 15,
        "tokens": 50000,
        "subprocess_calls": 30,
        "time_seconds": 120.0,
    },
    "confidence": 0.85,
    "within_budget": true,
}
```

#### Optimization API

```python
# POST /api/v1/optimize
{
    "objective": "minimize_cost",
    "constraints": [...],
    "parameters": {...},
}

# Response
{
    "optimal_parameters": {...},
    "optimal_value": 42.5,
    "iterations": 150,
    "success": true,
}
```

### 5.2 Database Schemas

#### Action Memory Schema (SQLite)

```sql
-- See Phase 8 section for complete schema
```

#### Run Artifacts Schema

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    repo_ref TEXT,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE patches (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    file_path TEXT NOT NULL,
    diff TEXT NOT NULL,
    applied BOOLEAN NOT NULL,
    verified BOOLEAN NOT NULL,
    tests_fixed INTEGER,
    tests_broken INTEGER
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id),
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

### 5.3 Configuration Formats

#### Full Configuration Schema

```yaml
# .rfsn.yaml schema
$schema: "https://rfsn.io/schemas/config-v1.json"

version: "1.0"

execution:
  max_steps: 12
  max_minutes: 30
  fix_all: false
  model: deepseek-chat
  time_mode: frozen

budget:
  max_llm_calls: 100
  max_tokens: 500000
  max_subprocess_calls: 200
  max_time_seconds: 1800
  warning_threshold: 0.8

contracts:
  enable_shell_contract: true
  enable_budget_contract: true
  enable_llm_contract: true
  enable_event_contract: true
  strict_mode: false

events:
  enabled: true
  output_dir: .rfsn/events
  max_events: 10000
  persist: true

memory:
  enabled: true
  db_path: .rfsn/memory.db
  prune_days: 30
  learning_enabled: true

optimizer:
  enabled: false
  solver: slsqp
  max_iterations: 1000
  tolerance: 1e-6

artifacts:
  output_dir: .rfsn/artifacts
  export_formats:
    - json
    - sarif
```

### 5.4 Integration Patterns

#### Event-Driven Integration

```python
# Pattern: Observer for cross-cutting concerns

class BudgetEventObserver:
    """Observes budget events and triggers actions."""
    
    def __init__(self, logger: EventLogger, optimizer: NonlinearOptimizer):
        self.logger = logger
        self.optimizer = optimizer
        self._register_handlers()
    
    def _register_handlers(self):
        self.logger.on_event(EventType.BUDGET_WARNING, self._handle_warning)
        self.logger.on_event(EventType.BUDGET_EXCEEDED, self._handle_exceeded)
    
    def _handle_warning(self, event: Event):
        # Trigger plan re-optimization
        self.optimizer.trigger_reoptimization()
```

#### Dependency Injection Pattern

```python
# Pattern: DI for testability

@dataclass
class ControllerDependencies:
    """Injectable dependencies for controller."""
    
    budget: Budget
    planner: Planner
    optimizer: NonlinearOptimizer
    memory: ActionMemoryStore
    event_logger: EventLogger
    artifact_store: ArtifactStore


def create_controller(deps: Optional[ControllerDependencies] = None) -> Controller:
    """Create controller with optional dependency injection."""
    if deps is None:
        deps = _create_default_dependencies()
    return Controller(deps)
```

---

## 6. Testing & Validation Strategy

### 6.1 Test Coverage Targets

| Component | Unit Tests | Integration Tests | Coverage Target |
|-----------|------------|-------------------|-----------------|
| Cost Estimator | 60+ | 20+ | 95% |
| Budget Optimizer | 50+ | 15+ | 95% |
| Nonlinear Optimizer | 80+ | 30+ | 90% |
| Action Memory | 50+ | 20+ | 95% |
| CLI | 40+ | 15+ | 90% |
| Artifact Model | 50+ | 20+ | 95% |
| Stage 5 Features | 100+ | 50+ | 85% |

### 6.2 Integration Test Approach

```python
# Integration test example

@pytest.mark.integration
class TestBudgetAwarePlanning:
    """Integration tests for budget-aware planning."""
    
    def test_plan_respects_budget_limits(self, test_repo, budget):
        """Plan should not exceed budget limits."""
        planner = BudgetAwarePlanner(ctx, budget)
        dag = planner.generate_plan(problem)
        
        estimated_cost = planner.cost_estimator.estimate_plan_cost(dag)
        remaining = budget.get_remaining()
        
        assert estimated_cost.llm_calls <= remaining.llm_calls
        assert estimated_cost.tokens <= remaining.tokens
    
    def test_plan_adapts_to_tight_budget(self, test_repo, tight_budget):
        """Plan should adapt when budget is tight."""
        planner = BudgetAwarePlanner(ctx, tight_budget)
        dag = planner.generate_plan(problem)
        
        # Should produce smaller plan
        assert len(dag.nodes) < 10
```

### 6.3 Performance Benchmarks

| Operation | Target Latency | Throughput |
|-----------|----------------|------------|
| Cost estimation (single node) | < 5ms | 200/sec |
| Plan optimization | < 100ms | 10/sec |
| Nonlinear optimization (100 vars) | < 1s | 1/sec |
| Memory query (1000 records) | < 50ms | 20/sec |
| Artifact save | < 100ms | 10/sec |
| Event logging | < 1ms | 1000/sec |

### 6.4 Test Automation

```yaml
# .github/workflows/test.yml additions

- name: Run Stage 3 Tests
  run: |
    pytest tests/test_cost_estimator.py -v
    pytest tests/test_budget_optimizer.py -v
    pytest tests/test_optimizer.py -v
    
- name: Run Stage 4 Tests
  run: |
    pytest tests/test_action_memory.py -v
    pytest tests/test_cli.py -v
    pytest tests/test_artifacts.py -v
    
- name: Run Performance Benchmarks
  run: |
    pytest tests/benchmarks/ --benchmark-json=benchmark.json
```

---

## 7. Risk Assessment & Mitigation

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Optimizer convergence issues | Medium | Medium | Multiple solver backends, restart strategies |
| Memory database performance | Low | High | Indexing, query optimization, connection pooling |
| CLI backward compatibility | Medium | Medium | Semantic versioning, deprecation warnings |
| Integration complexity | High | Medium | Incremental integration, feature flags |
| Test flakiness | Medium | Low | Deterministic tests, retry mechanisms |

### 7.2 Complexity Management

**Strategies:**
1. **Feature Flags** - All new features behind flags for gradual rollout
2. **Modular Design** - Loose coupling between components
3. **Interface Stability** - Stable interfaces with versioning
4. **Documentation** - Comprehensive docs for each component

### 7.3 Backward Compatibility

**Compatibility Matrix:**

| Change Type | Approach |
|-------------|----------|
| New API methods | Additive, no breaking changes |
| Config changes | New fields optional, defaults provided |
| CLI changes | New commands, deprecation period for removals |
| Database schema | Migration scripts, backward-compatible changes |

**Migration Path:**

```python
# Version compatibility layer
class CompatibilityLayer:
    """Provides backward compatibility for API changes."""
    
    @staticmethod
    def migrate_config_v1_to_v2(config: Dict) -> Dict:
        """Migrate v1 config to v2 format."""
        ...
    
    @staticmethod
    def deprecation_warning(feature: str, replacement: str) -> None:
        """Emit deprecation warning."""
        warnings.warn(
            f"{feature} is deprecated, use {replacement} instead",
            DeprecationWarning,
            stacklevel=3,
        )
```

---

## 8. Implementation Roadmap

### 8.1 Phased Rollout Plan

```
Phase 6 (Weeks 1-5): Planner Budget Tracking
├── Week 1-2: Cost estimation system
├── Week 3: Budget optimizer
├── Week 4: Integration
└── Week 5: Testing & documentation

Phase 7 (Weeks 6-9): Nonlinear Optimizer
├── Week 6-7: Core optimizer implementation
├── Week 8: Objective functions & constraints
└── Week 9: Integration & testing

Phase 8 (Weeks 10-13): Action-Outcome Memory
├── Week 10-11: Enhanced storage
├── Week 12: Metrics analyzer
└── Week 13: Integration & testing

Phase 9 (Weeks 14-16): Stable CLI
├── Week 14: CLI refactoring
├── Week 15: Configuration system
└── Week 16: Testing & documentation

Phase 10 (Weeks 17-20): Run Artifacts
├── Week 17-18: Artifact model
├── Week 19: Export formats
└── Week 20: Integration & testing

Stage 5 (Weeks 21-45): Advanced Features
├── Weeks 21-23: v2 - Attestation & gates
├── Weeks 24-26: v3 - Policy versioning & bot
├── Weeks 27-28: v4 - SARIF & governance
├── Weeks 29-30: v5 - Two-person control
├── Weeks 31-35: v6 - Multi-tenant
├── Weeks 36-40: v7 - Distributed runners
├── Weeks 41-43: v8 - Policy-aware learning
├── Weeks 44-47: v9 - HITL operations
└── Weeks 48-50: v10 - UX polish
```

### 8.2 Dependencies Between Stages

```
Stage 3: Planning & Optimization
├── Phase 6 (Budget Tracking) ─────┬──────────────────────┐
│                                   │                      │
└── Phase 7 (Optimizer) ───────────┴─┐                    │
                                      │                    │
Stage 4: Memory & Artifacts           │                    │
├── Phase 8 (Memory) ◄────────────────┘                    │
│       │                                                   │
├── Phase 9 (CLI) ◄────────────────────────────────────────┤
│       │                                                   │
└── Phase 10 (Artifacts) ◄──────────────────────────────────┘
        │
Stage 5: Advanced Features
├── v2 (Attestation) ◄────────────────────────────────────┐
├── v3 (Policy/Bot) ◄──────────────────────────────────┐  │
├── v4 (SARIF) ◄──────────────────────────────────────┐│  │
├── v5 (Two-Person) ◄────────────────────────────────┐││  │
├── v6 (Multi-Tenant) ◄─────────────────────────────┐│││  │
├── v7 (Distributed) ◄──────────────────────────────│├┘│  │
├── v8 (Learning) ◄─────────────────────────────────├┤ │  │
├── v9 (HITL) ◄─────────────────────────────────────└┤ │  │
└── v10 (UX) ◄───────────────────────────────────────└─┴──┘
```

### 8.3 Recommended Order of Implementation

**Critical Path:**
1. Phase 6 → Phase 7 (Optimizer depends on cost estimation)
2. Phase 8 → v8 (Learning depends on memory)
3. Phase 10 → v2, v3, v4 (Artifacts needed for attestation, SARIF)
4. v6 → v7 (Distributed depends on multi-tenant)

**Parallel Tracks:**
- Track A: Phases 6, 7, 8 (Core infrastructure)
- Track B: Phases 9, 10 (CLI and artifacts)
- Track C: v2-v5 (Governance features)
- Track D: v6-v7 (Scaling features)
- Track E: v8-v10 (Intelligence and UX)

### 8.4 Milestone Definitions

| Milestone | Criteria | Target Date |
|-----------|----------|-------------|
| M1: Stage 3 Complete | Phases 6-7 merged, 90%+ coverage | End of Week 9 |
| M2: Stage 4 Complete | Phases 8-10 merged, stable CLI | End of Week 20 |
| M3: Governance Ready | v2-v5 complete | End of Week 30 |
| M4: Scale Ready | v6-v7 complete | End of Week 40 |
| M5: Production Ready | v8-v10 complete | End of Week 50 |

---

## Appendix A: File Inventory

### New Files (Stage 3)

```
rfsn_controller/
├── cost_estimator.py      # Phase 6
├── budget_optimizer.py    # Phase 6
├── optimizer.py           # Phase 7
├── objectives.py          # Phase 7
├── constraints.py         # Phase 7

tests/
├── test_cost_estimator.py
├── test_budget_optimizer.py
├── test_optimizer.py
├── test_objectives.py
```

### New Files (Stage 4)

```
rfsn_controller/
├── artifact_model.py      # Phase 10
├── artifact_store.py      # Phase 10
├── sarif_exporter.py      # Phase 10

tests/
├── test_action_memory_v2.py
├── test_cli_v2.py
├── test_artifacts.py
```

### New Files (Stage 5)

```
rfsn_controller/
├── attestation.py         # v2
├── promotion.py           # v2
├── policy_version.py      # v3
├── patch_bot.py           # v3
├── dependency_gov.py      # v4
├── two_person.py          # v5
├── multi_tenant.py        # v6
├── worker.py              # v6
├── distributed.py         # v7
├── policy_learner.py      # v8
├── hitl.py                # v9
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| DAG | Directed Acyclic Graph - execution plan structure |
| HITL | Human-in-the-Loop - human oversight workflow |
| SARIF | Static Analysis Results Interchange Format |
| Cost Estimation | Predicting resource usage before execution |
| Budget Reservation | Pre-allocating budget for planned operations |
| Attestation | Cryptographic proof of run authenticity |
| Promotion Gate | Checkpoint requiring approval before deployment |

---

## Appendix C: References

1. SARIF Specification: https://sarifweb.azurewebsites.net/
2. scipy.optimize documentation: https://docs.scipy.org/doc/scipy/reference/optimize.html
3. Click CLI framework: https://click.palletsprojects.com/
4. SQLite optimization: https://www.sqlite.org/optoverview.html

---

*Document maintained by the RFSN Controller team. For questions, contact the technical lead.*
