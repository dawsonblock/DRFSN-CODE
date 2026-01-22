# RFSN-CODING Stage 1 Implementation Plan

## Executive Summary

This document outlines the implementation plan for Stage 1 of the RFSN-CODING project security hardening initiative. Stage 1 consists of three critical phases:

1. **Phase 1: Shell Elimination** - Replace all shell=True subprocess calls with argv-only execution
2. **Phase 2: Testing Infrastructure** - Create scan_for_shell_violations utility and comprehensive tests
3. **Phase 3: Budget Gates** - Implement Budget class, BudgetState, BudgetExceeded exception, and budget tracking

---

## Codebase Analysis

### Project Structure Overview

```
rfsn_coding/
├── rfsn_controller/          # Main package (61 Python files)
│   ├── buildpacks/           # Language-specific build support (8 files)
│   ├── exec_utils.py         # ✅ Already has safe execution utilities
│   ├── sandbox.py            # Core sandbox execution (uses _run helper)
│   ├── config.py             # Configuration dataclasses
│   ├── context.py            # Runtime context management
│   ├── controller.py         # Main controller loop
│   └── ... (50+ other modules)
├── tests/                    # Test suite (19 test files)
│   ├── test_no_shell.py      # ✅ Existing shell pattern scanner
│   └── ...
├── rfsn_dashboard/           # Dashboard web app (2 files)
└── scripts/                  # Utility scripts (2 files)
```

### Total Python Files: 90 files

---

## Phase 1: Shell Elimination Analysis

### Current State Assessment

**GOOD NEWS**: The codebase already follows good security practices for the most part. The `exec_utils.py` module already enforces:
- Commands must be argv lists
- No shell=True allowed
- No sh -c or bash -c wrappers
- Allowlist enforcement
- Sanitized environment

### Files with subprocess.run/Popen Calls

| File | Line(s) | Current State | Action Required |
|------|---------|---------------|-----------------|
| `exec_utils.py` | 146 | ✅ `shell=False` explicit | None - Already secure |
| `sandbox.py` | 130, 623, 677, 836 | ✅ Uses `shlex.split()` + `shell=False` | None - Already secure |
| `services_lane.py` | 457, 504, 558, 586, 634 | ✅ Uses argv lists | None - Already secure |
| `performance.py` | 60, 75, 160, 218, 262, 268, 308 | ✅ Uses argv lists | None - Already secure |
| `sysdeps_installer.py` | 143, 186 | ✅ Uses argv lists | None - Already secure |
| `smart_file_cache.py` | 309, 345 | ✅ Uses argv lists | None - Already secure |
| **`optimizations.py`** | 103-104 | ⚠️ **`["/bin/bash", "-i"]`** | **NEEDS REFACTORING** |

### Issue Found: SubprocessPool in optimizations.py

**Location**: `rfsn_controller/optimizations.py` lines 100-111

```python
def _create_worker(self) -> SubprocessWorker:
    """Create a new subprocess worker."""
    # Create a persistent bash process
    process = subprocess.Popen(
        ["/bin/bash", "-i"],  # <-- SECURITY CONCERN
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
    )
    return SubprocessWorker(process=process, last_used=time.time())
```

**Problem**: Creates persistent interactive bash shells for command pooling. While not using `shell=True`, the `-i` flag creates interactive shells that could be security concerns.

**Recommended Fix**: Either:
1. Remove the SubprocessPool entirely (it's not heavily used)
2. Refactor to not use interactive shells, use direct command execution instead
3. Mark this as intentional with security documentation if the pooling is critical for performance

### Files That Need Modification for Phase 1

| Priority | File | Modification |
|----------|------|--------------|
| HIGH | `rfsn_controller/optimizations.py` | Refactor SubprocessPool to avoid interactive shells |

---

## Phase 2: Testing Infrastructure

### Existing Test Coverage

The project already has a strong test infrastructure:

- **`test_no_shell.py`**: Scans codebase for forbidden patterns using regex and AST
- **`test_shell_idiom_validation.py`**: Additional shell idiom tests
- **`test_zero_trust_hardening.py`**: Security hardening tests
- **`test_security_and_verification.py`**: Verification tests

### New Testing Requirements

#### 1. Create `scan_for_shell_violations` Utility

**Location**: `rfsn_controller/shell_scanner.py` (new file)

This will be a standalone utility that can be:
- Used in CI/CD pipelines
- Run as a pre-commit hook
- Called from tests

**Features to implement**:
- AST-based detection of subprocess calls with shell=True
- Pattern detection for sh -c, bash -c, os.system, os.popen
- Report generation with file locations
- Exit code for CI integration

#### 2. Enhance pytest Configuration

**Updates to `pyproject.toml`**:
- Add `security` marker for security-related tests
- Configure coverage reporting

#### 3. New Test Files to Create

| File | Purpose |
|------|---------|
| `tests/test_budget_gates.py` | Tests for Budget class and enforcement |
| `tests/test_shell_scanner.py` | Tests for the shell violation scanner |
| `tests/unit/test_exec_utils.py` | Unit tests for exec_utils functions |

---

## Phase 3: Budget Gates Architecture

### Design Overview

Budget gates will track and enforce resource consumption limits across the controller execution.

### Core Classes

#### 1. BudgetState Enum

```python
from enum import Enum, auto

class BudgetState(Enum):
    """States a budget can be in."""
    ACTIVE = auto()      # Budget is active and has capacity
    WARNING = auto()     # Budget is approaching limits
    EXCEEDED = auto()    # Budget has been exceeded
    EXHAUSTED = auto()   # Budget is completely exhausted
```

#### 2. BudgetExceeded Exception

```python
class BudgetExceeded(Exception):
    """Raised when a budget limit is exceeded."""
    
    def __init__(
        self,
        budget_name: str,
        limit: float,
        current: float,
        resource_type: str,
    ):
        self.budget_name = budget_name
        self.limit = limit
        self.current = current
        self.resource_type = resource_type
        super().__init__(
            f"Budget '{budget_name}' exceeded: {resource_type} "
            f"at {current:.2f}/{limit:.2f}"
        )
```

#### 3. Budget Class

```python
@dataclass
class Budget:
    """Resource budget with tracking and enforcement."""
    
    name: str
    
    # Resource limits
    max_steps: int = 100
    max_llm_calls: int = 50
    max_tokens: int = 1_000_000
    max_time_seconds: float = 3600.0
    max_subprocess_calls: int = 500
    
    # Current consumption
    steps_used: int = 0
    llm_calls_used: int = 0
    tokens_used: int = 0
    subprocess_calls_used: int = 0
    start_time: float = field(default_factory=time.time)
    
    # Warning thresholds (percentage)
    warning_threshold: float = 0.8
    
    def check_step(self) -> BudgetState
    def check_llm_call(self, tokens: int = 0) -> BudgetState
    def check_subprocess(self) -> BudgetState
    def check_time(self) -> BudgetState
    def consume_step(self) -> None
    def consume_llm_call(self, tokens: int) -> None
    def consume_subprocess(self) -> None
    def get_state(self) -> BudgetState
    def to_dict(self) -> Dict[str, Any]
```

### Integration Points

Budget tracking needs to be integrated at these locations:

| Integration Point | File | Function/Method | Budget Type |
|-------------------|------|-----------------|-------------|
| Controller loop | `controller.py` | Main loop | `consume_step()` |
| LLM calls | `llm_gemini.py` | `call_model()` | `consume_llm_call()` |
| LLM calls | `llm_deepseek.py` | `call_model()` | `consume_llm_call()` |
| Command execution | `exec_utils.py` | `safe_run()` | `consume_subprocess()` |
| Sandbox commands | `sandbox.py` | `_run()` | `consume_subprocess()` |
| Docker commands | `services_lane.py` | Various | `consume_subprocess()` |

### Configuration Integration

Add budget configuration to `config.py`:

```python
@dataclass
class BudgetConfig:
    """Budget configuration for resource limits."""
    
    max_steps: int = 100
    max_llm_calls: int = 50
    max_tokens: int = 1_000_000
    max_time_seconds: float = 3600.0
    max_subprocess_calls: int = 500
    warning_threshold: float = 0.8
    enforce: bool = True  # Whether to raise exceptions on exceed
```

### Context Integration

Add budget to `context.py`:

```python
@dataclass
class ControllerContext:
    # ... existing fields ...
    
    _budget: Optional["Budget"] = field(default=None, repr=False)
    
    @property
    def budget(self) -> Optional["Budget"]:
        """Get the budget tracker."""
        return self._budget
    
    @budget.setter
    def budget(self, value: "Budget") -> None:
        """Set the budget tracker."""
        self._budget = value
        self.event_log.emit("budget_set", limits=value.to_dict())
```

---

## Implementation Files Summary

### New Files to Create

| File | Phase | Purpose |
|------|-------|---------|
| `rfsn_controller/budget.py` | 3 | Budget, BudgetState, BudgetExceeded |
| `rfsn_controller/shell_scanner.py` | 2 | Shell violation scanner utility |
| `tests/test_budget_gates.py` | 3 | Budget enforcement tests |
| `tests/test_shell_scanner.py` | 2 | Shell scanner tests |
| `tests/unit/test_exec_utils.py` | 2 | exec_utils unit tests |

### Files to Modify

| File | Phase | Modification |
|------|-------|--------------|
| `rfsn_controller/optimizations.py` | 1 | Refactor/remove SubprocessPool |
| `rfsn_controller/config.py` | 3 | Add BudgetConfig |
| `rfsn_controller/context.py` | 3 | Add budget property |
| `rfsn_controller/controller.py` | 3 | Integrate budget tracking |
| `rfsn_controller/exec_utils.py` | 3 | Add optional budget tracking |
| `rfsn_controller/sandbox.py` | 3 | Add optional budget tracking |
| `rfsn_controller/llm_gemini.py` | 3 | Add budget tracking |
| `rfsn_controller/llm_deepseek.py` | 3 | Add budget tracking |
| `pyproject.toml` | 2 | Add security test marker |

---

## Execution Plan

### Phase 1: Shell Elimination (Estimated: 1-2 hours)

1. ✅ Audit complete - only `optimizations.py` needs changes
2. Refactor `SubprocessPool` in `optimizations.py`:
   - Option A: Remove entirely if not critical
   - Option B: Replace with non-interactive approach
3. Run existing `test_no_shell.py` to verify
4. Commit changes

### Phase 2: Testing Infrastructure (Estimated: 2-3 hours)

1. Create `shell_scanner.py` utility module
2. Create `tests/test_shell_scanner.py`
3. Create `tests/unit/test_exec_utils.py`
4. Update `pyproject.toml` with new markers
5. Run full test suite
6. Commit changes

### Phase 3: Budget Gates (Estimated: 3-4 hours)

1. Create `rfsn_controller/budget.py` with:
   - `BudgetState` enum
   - `BudgetExceeded` exception
   - `Budget` class
2. Update `config.py` with `BudgetConfig`
3. Update `context.py` with budget property
4. Integrate budget tracking into:
   - `exec_utils.py`
   - `sandbox.py`
   - `llm_gemini.py`
   - `llm_deepseek.py`
   - `controller.py`
5. Create `tests/test_budget_gates.py`
6. Run full test suite
7. Commit changes

---

## Dependencies

### Python Package Requirements

All required packages are already in `pyproject.toml`:
- `pytest>=7.0.0` (for testing)
- No additional packages needed for budget implementation

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SubprocessPool removal breaks performance | Low | Medium | Profile before/after; keep code commented if needed |
| Budget tracking adds overhead | Low | Low | Use lightweight dataclass; measure impact |
| False positives in shell scanner | Medium | Low | Use AST parsing for accuracy |

---

## Success Criteria

### Phase 1 Complete When:
- [ ] No subprocess calls use shell=True or interactive shells
- [ ] `test_no_shell.py` passes
- [ ] All existing tests pass

### Phase 2 Complete When:
- [ ] `shell_scanner.py` utility exists and works
- [ ] Shell scanner has comprehensive tests
- [ ] CI can fail on shell violations

### Phase 3 Complete When:
- [ ] `Budget` class tracks all resource types
- [ ] `BudgetExceeded` raised when limits hit
- [ ] Integration in controller loop works
- [ ] All budget tests pass

---

## Appendix: Module Purposes

### Core Modules

| Module | Purpose |
|--------|---------|
| `controller.py` | Main controller loop orchestrating the agent |
| `sandbox.py` | Disposable sandbox for git/filesystem operations |
| `exec_utils.py` | Safe subprocess execution with allowlists |
| `config.py` | Configuration dataclasses |
| `context.py` | Runtime context management |

### LLM Integration

| Module | Purpose |
|--------|---------|
| `llm_gemini.py` | Google Gemini API client |
| `llm_deepseek.py` | DeepSeek API client |
| `llm_async.py` | Async LLM utilities |
| `llm_ensemble.py` | Multi-model ensemble |

### Security

| Module | Purpose |
|--------|---------|
| `command_allowlist.py` | Global command allowlist |
| `command_normalizer.py` | Command normalization |
| `apt_whitelist.py` | APT package whitelist |
| `security_hardening.py` | Security hardening utilities |
| `url_validation.py` | URL security validation |

### Build Support

| Module | Purpose |
|--------|---------|
| `buildpacks/base.py` | Base buildpack class |
| `buildpacks/python_pack.py` | Python project support |
| `buildpacks/node_pack.py` | Node.js project support |
| `buildpacks/rust_pack.py` | Rust project support |
| `buildpacks/go_pack.py` | Go project support |
| `buildpacks/java_pack.py` | Java project support |
| `buildpacks/dotnet_pack.py` | .NET project support |

---

*Document generated: January 20, 2026*
*Project: RFSN-CODING Stage 1 Implementation*
