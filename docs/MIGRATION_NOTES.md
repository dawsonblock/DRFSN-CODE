# Migration Notes (Stage 1 & Stage 2)

This document describes breaking changes and migration steps for code affected by Stage 1 and Stage 2 upgrades.

## Breaking Changes

### 1. SubprocessPool Command Execution

**Change**: SubprocessPool no longer accepts shell wrappers or interactive shell patterns.

**Before (now fails)**:
```python
from rfsn_controller.optimizations import get_subprocess_pool

pool = get_subprocess_pool()

# These will now raise ValueError:
pool.run_command(["sh", "-c", "echo hello"])
pool.run_command(["bash", "-c", "ls | grep py"])
pool.run_command(["/bin/bash", "-i"])
```

**After (required)**:
```python
from rfsn_controller.optimizations import get_subprocess_pool

pool = get_subprocess_pool()

# Use direct command lists:
pool.run_command(["echo", "hello"])
pool.run_command(["ls", "-la"])  # For simple listing
```

**Migration Steps**:
1. Search your code for `run_command` calls with shell wrappers
2. Replace `sh -c` patterns with direct command lists
3. For pipelines, consider Python alternatives or use individual commands

### 2. exec_utils Command Validation

**Change**: `safe_run()` now validates all commands and rejects shell wrappers.

**Before (now fails)**:
```python
from rfsn_controller.exec_utils import safe_run

# These will now raise ValueError:
safe_run(["sh", "-c", "complex command"])
safe_run(["bash", "-i"])
```

**After (required)**:
```python
from rfsn_controller.exec_utils import safe_run

# Use direct commands:
safe_run(["complex_command", "arg1", "arg2"])

# For complex logic, use Python:
result = safe_run(["cmd1", "arg"])
if result.returncode == 0:
    result2 = safe_run(["cmd2", result.stdout.strip()])
```

### 3. Budget Limits May Interrupt Operations

**Change**: Operations may now raise `BudgetExceeded` if limits are configured.

**Impact**: Code that doesn't handle this exception may terminate unexpectedly.

**Migration Steps**:
```python
from rfsn_controller.budget import BudgetExceeded

try:
    # Your operation that uses subprocess/LLM
    result = safe_run(["some", "command"])
except BudgetExceeded as e:
    # Handle gracefully
    logger.warning(f"Budget exceeded: {e.resource}")
    # Cleanup or partial result handling
```

---

## Deprecations

### 1. Raw subprocess.Popen with stdin

**Deprecated**: Creating persistent shell processes and writing commands to stdin.

**Reason**: Security vulnerability - allows command injection.

**Alternative**: Use `safe_run()` or `SubprocessPool.run_command()` for each command.

### 2. Direct subprocess.run with shell=True

**Deprecated**: Using `shell=True` parameter.

**Reason**: Enables shell injection attacks.

**Alternative**: 
```python
# Instead of:
subprocess.run(f"ls {path}", shell=True)

# Use:
subprocess.run(["ls", path], shell=False)
# Or:
safe_run(["ls", path])
```

---

## New Dependencies

Stage 1 adds the following development dependencies:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-timeout>=2.0",
]
```

Install with:
```bash
pip install -e ".[dev]"
```

---

## Configuration Changes

### New CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--max-steps` | int | 0 | Maximum iteration steps (0=unlimited) |
| `--max-llm-calls` | int | 0 | Maximum LLM API calls |
| `--max-tokens` | int | 0 | Maximum tokens used |
| `--max-time` | int | 0 | Maximum time in seconds |
| `--max-subprocess-calls` | int | 0 | Maximum subprocess executions |
| `--budget-warning-threshold` | float | 0.8 | Warning at this % of limit |

### Config Object Changes

`ControllerConfig` now includes:
```python
@dataclass(frozen=True)
class ControllerConfig:
    # ... existing fields ...
    budget: BudgetConfig = field(default_factory=BudgetConfig)
```

`BudgetConfig` is new:
```python
@dataclass(frozen=True)
class BudgetConfig:
    max_steps: int = 0
    max_llm_calls: int = 0
    max_tokens: int = 0
    max_time_seconds: int = 0
    max_subprocess_calls: int = 0
    warning_threshold: float = 0.8
```

---

## Test Configuration Changes

### pytest Markers

New markers are available:
```python
@pytest.mark.unit      # Unit tests
@pytest.mark.security  # Security-related tests
@pytest.mark.scanner   # Shell scanner tests
```

### Coverage Requirements

`pyproject.toml` now enforces minimum coverage:
```toml
[tool.coverage.report]
fail_under = 60
```

---

## API Changes

### New Module: rfsn_controller.budget

Exports:
- `Budget` - Main budget tracking class
- `BudgetState` - Enum (ACTIVE, WARNING, EXCEEDED, EXHAUSTED)
- `BudgetExceeded` - Exception class
- `create_budget()` - Factory function
- `set_global_budget()` - Set global budget instance
- `get_global_budget()` - Get global budget instance
- `record_subprocess_call_global()` - Track subprocess call
- `record_llm_call_global()` - Track LLM call
- `check_time_budget_global()` - Check time limit

### New Module: rfsn_controller.shell_scanner

Exports:
- `ShellScanner` - Scanner class
- `Violation` - Dataclass for detected issues
- `ScanResult` - Dataclass for scan results
- `main()` - CLI entry point

### Modified Modules

#### exec_utils.py
- `safe_run()` now calls `record_subprocess_call_global()` before execution

#### sandbox.py
- Internal `_run()` calls `record_subprocess_call_global()` before execution

#### llm_gemini.py / llm_deepseek.py
- `call_model()` and `call_model_async()` now call `record_llm_call_global(tokens)`

#### context.py
- `ControllerContext` has new `budget` property
- `create_context()` initializes budget from config

---

## Known Issues

### Shell Scanner False Positives

The scanner may flag intentional `sh -c` patterns that are safe:
- Docker container commands
- Buildpack fallback commands

Exclude these with:
```bash
python -m rfsn_controller.shell_scanner . --exclude-file sandbox.py
```

### Budget Callbacks and Thread Safety

Budget callbacks execute inline with the recording call. Long-running callbacks may impact performance. Consider:
```python
def quick_callback(resource, used, limit):
    # Queue for async handling instead of blocking
    async_queue.put((resource, used, limit))
```

---

## Rollback Instructions

If Stage 1 causes issues and you need to rollback:

1. **Git revert**: Revert to the commit before Stage 1 changes
2. **Remove new files**:
   ```bash
   rm rfsn_controller/budget.py
   rm rfsn_controller/shell_scanner.py
   rm tests/test_budget_gates.py
   rm tests/test_shell_scanner.py
   rm tests/unit/test_exec_utils.py
   rm tests/unit/test_subprocess_pool.py
   ```
3. **Restore original files** from backup

---

## Getting Help

If you encounter migration issues:

1. Check the test files for usage examples
2. Review [USAGE_GUIDE.md](USAGE_GUIDE.md) for detailed documentation
3. Search for related tests in `tests/` directory
4. Open an issue with the specific error message

---

# Stage 2 Migration Notes

## Breaking Changes (Stage 2)

### 4. Contract Enforcement in exec_utils

**Change**: `safe_run()` now validates commands against the global contract validator when configured.

**Impact**: Shell wrappers now raise `ContractViolation` instead of `ValueError`.

**Migration Steps**:
```python
from rfsn_controller.contracts import ContractViolation

try:
    safe_run(["some", "command"])
except ContractViolation as e:
    # Handle contract violation
    logger.error(f"Contract {e.contract_name} violated: {e.details}")
except ValueError as e:
    # Still possible for basic validation errors
    logger.error(f"Invalid command: {e}")
```

### 5. Global Logger Initialization

**Change**: Event logging is opt-in but recommended. Not initializing may cause log events to be silently dropped.

**Migration Steps**:
```python
from rfsn_controller.events import EventLogger, set_global_logger

# Initialize at application startup
logger = EventLogger(run_id="my-run-001")
set_global_logger(logger)
```

---

## New Dependencies (Stage 2)

No new external dependencies for Stage 2. All features use standard library.

---

## Configuration Changes (Stage 2)

### New CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--enable-shell-contract` | flag | True | Enable shell execution contract |
| `--enable-budget-contract` | flag | True | Enable budget tracking contract |
| `--enable-llm-contract` | flag | True | Enable LLM calling contract |
| `--enable-event-contract` | flag | True | Enable event logging contract |
| `--strict-contracts` | flag | False | All violations are fatal |
| `--no-contracts` | flag | False | Disable all contracts |

### Config Object Changes

`ControllerConfig` now includes:
```python
@dataclass(frozen=True)
class ControllerConfig:
    # ... existing fields ...
    contract: ContractConfig = field(default_factory=ContractConfig)
```

`ContractConfig` is new:
```python
@dataclass(frozen=True)
class ContractConfig:
    enable_shell_contract: bool = True
    enable_budget_contract: bool = True
    enable_llm_contract: bool = True
    enable_event_contract: bool = True
    strict_mode: bool = False
```

---

## API Changes (Stage 2)

### New Module: rfsn_controller.events

Exports:
- `Event` - Event dataclass
- `EventType` - Enum for event types
- `EventSeverity` - Enum for severity levels
- `EventLogger` - In-memory event collection
- `EventStore` - File-based event persistence
- `EventQuery` - Event filtering and querying
- `create_event()` - Factory function
- `set_global_logger()` / `get_global_logger()` - Global logger management
- `log_event_global()` - Log events globally
- `log_controller_step_global()` - Log controller steps
- `log_llm_call_global()` - Log LLM calls
- `log_budget_warning_global()` - Log budget warnings
- `log_subprocess_exec_global()` - Log subprocess executions
- `log_security_violation_global()` - Log security violations
- `log_error_global()` - Log errors

### New Module: rfsn_controller.contracts

Exports:
- `FeatureContract` - Contract dataclass
- `ContractConstraint` - Enum for constraints
- `ContractViolation` - Exception class
- `ContractRegistry` - Contract management
- `ContractValidator` - Validation logic
- `get_global_registry()` / `set_global_registry()` - Global registry
- `get_global_validator()` / `set_global_validator()` - Global validator
- `register_standard_contracts()` - Register pre-built contracts
- Standard contracts: `SHELL_EXECUTION_CONTRACT`, `BUDGET_TRACKING_CONTRACT`, `LLM_CALLING_CONTRACT`, `EVENT_LOGGING_CONTRACT`

### Modified Modules (Stage 2)

#### config.py
- Added `ContractConfig` dataclass
- `ControllerConfig` now has `contract` field
- `config_from_cli_args()` parses contract flags

#### context.py
- Added `contract_registry` and `contract_validator` properties
- `create_context()` initializes contract system

#### controller.py
- Initializes contract registry and validator
- Registers standard contracts based on config

#### exec_utils.py
- `safe_run()` validates against global contract validator
- Logs SUBPROCESS_EXEC events when global logger is set

---

## Rollback Instructions (Stage 2)

If Stage 2 causes issues:

1. **Git revert**: Revert Stage 2 commits
2. **Remove new files**:
   ```bash
   rm rfsn_controller/events.py
   rm rfsn_controller/contracts.py
   rm tests/test_events.py
   rm tests/test_contracts.py
   ```
3. **Revert modified files**: 
   - `config.py`, `context.py`, `controller.py`, `exec_utils.py`

---

*Migration Notes - January 2026*
