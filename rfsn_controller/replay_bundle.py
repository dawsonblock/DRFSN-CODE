"""Deterministic replay bundles for reproducible debugging.

Captures complete environment state for exact attempt reproduction:
- Git revision and dirty state
- Docker/container digest
- Environment variables snapshot
- Install commands executed
- Test commands and outputs
- Seed values for reproducibility
"""

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EnvironmentSnapshot:
    """Captured environment state for replay."""

    # Python/runtime info
    python_version: str = ""
    pip_freeze: List[str] = field(default_factory=list)
    
    # Git state
    git_revision: str = ""
    git_branch: str = ""
    git_dirty: bool = False
    git_diff_head: str = ""  # Uncommitted changes
    
    # Container info (if applicable)
    docker_image: str = ""
    docker_digest: str = ""
    
    # Environment variables (filtered for safety)
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # Install commands executed during setup
    install_commands: List[str] = field(default_factory=list)


@dataclass
class TestExecution:
    """Captured test execution for replay comparison."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timestamp: str


@dataclass
class AttemptReplayBundle:
    """Complete bundle for deterministic replay of an attempt.
    
    Contains all state needed to reproduce an exact controller run,
    including the environment, inputs, and expected outputs.
    """

    # Identification
    bundle_id: str
    run_id: str
    created_at: str
    
    # Environment state
    environment: EnvironmentSnapshot
    
    # Input state
    repo_url: str = ""
    repo_path: str = ""
    test_command: str = ""
    
    # Attempt details
    step_number: int = 0
    patch_diff: str = ""
    patch_hash: str = ""
    
    # Test executions (before and after patch)
    baseline_test: Optional[TestExecution] = None
    attempt_test: Optional[TestExecution] = None
    
    # Seed values for randomness
    seeds: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    controller_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# Environment variable prefixes to exclude from snapshots
ENV_EXCLUDE_PREFIXES = (
    "AWS_",
    "OPENAI_",
    "ANTHROPIC_",
    "GOOGLE_",
    "AZURE_",
    "SECRET",
    "TOKEN",
    "KEY",
    "PASSWORD",
    "CREDENTIAL",
)


def capture_environment(
    *,
    repo_path: str,
    docker_image: Optional[str] = None,
    install_commands: Optional[List[str]] = None,
) -> EnvironmentSnapshot:
    """Capture current environment state for replay.
    
    Args:
        repo_path: Path to the repository.
        docker_image: Docker image used (if any).
        install_commands: Install commands that were executed.
    
    Returns:
        EnvironmentSnapshot with current state.
    """
    import sys
    
    env = EnvironmentSnapshot()
    
    # Python version
    env.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Pip freeze
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            env.pip_freeze = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except Exception:
        pass
    
    # Git state
    try:
        # Revision
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=10,
        )
        if result.returncode == 0:
            env.git_revision = result.stdout.strip()
        
        # Branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=10,
        )
        if result.returncode == 0:
            env.git_branch = result.stdout.strip()
        
        # Dirty check
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=10,
        )
        if result.returncode == 0:
            env.git_dirty = bool(result.stdout.strip())
            
            # Capture uncommitted changes if dirty
            if env.git_dirty:
                result = subprocess.run(
                    ["git", "diff", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                    timeout=30,
                )
                if result.returncode == 0:
                    env.git_diff_head = result.stdout[:50000]  # Limit size
    except Exception:
        pass
    
    # Docker info
    if docker_image:
        env.docker_image = docker_image
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format={{.Id}}", docker_image],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                env.docker_digest = result.stdout.strip()
        except Exception:
            pass
    
    # Environment variables (filtered)
    for key, value in os.environ.items():
        if not any(key.upper().startswith(prefix) for prefix in ENV_EXCLUDE_PREFIXES):
            env.env_vars[key] = value
    
    # Install commands
    if install_commands:
        env.install_commands = list(install_commands)
    
    return env


def create_replay_bundle(
    *,
    run_id: str,
    step_number: int,
    repo_path: str,
    test_command: str,
    patch_diff: str,
    baseline_test: Optional[TestExecution] = None,
    attempt_test: Optional[TestExecution] = None,
    docker_image: Optional[str] = None,
    install_commands: Optional[List[str]] = None,
    repo_url: str = "",
    seeds: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AttemptReplayBundle:
    """Create a replay bundle for the current attempt.
    
    Args:
        run_id: Controller run ID.
        step_number: Step number in the repair loop.
        repo_path: Path to the repository.
        test_command: Test command being run.
        patch_diff: The patch being applied.
        baseline_test: Test execution before patch.
        attempt_test: Test execution after patch.
        docker_image: Docker image used.
        install_commands: Commands used for setup.
        repo_url: Original repository URL.
        seeds: Random seeds used.
        metadata: Additional metadata.
    
    Returns:
        AttemptReplayBundle ready for export.
    """
    # Generate bundle ID from content hash
    content_for_hash = f"{run_id}:{step_number}:{patch_diff}"
    bundle_id = hashlib.sha256(content_for_hash.encode()).hexdigest()[:16]
    
    # Capture environment
    environment = capture_environment(
        repo_path=repo_path,
        docker_image=docker_image,
        install_commands=install_commands,
    )
    
    # Compute patch hash
    patch_hash = hashlib.sha256(patch_diff.encode()).hexdigest()[:16] if patch_diff else ""
    
    return AttemptReplayBundle(
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        environment=environment,
        repo_url=repo_url,
        repo_path=repo_path,
        test_command=test_command,
        step_number=step_number,
        patch_diff=patch_diff,
        patch_hash=patch_hash,
        baseline_test=baseline_test,
        attempt_test=attempt_test,
        seeds=seeds or {},
        controller_version=_get_controller_version(),
        metadata=metadata or {},
    )


def export_replay_bundle(bundle: AttemptReplayBundle, output_dir: str) -> str:
    """Export a replay bundle to disk.
    
    Args:
        bundle: The bundle to export.
        output_dir: Directory to write the bundle.
    
    Returns:
        Path to the exported bundle file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    bundle_filename = f"replay_{bundle.run_id}_{bundle.step_number}_{bundle.bundle_id}.json"
    bundle_path = os.path.join(output_dir, bundle_filename)
    
    with open(bundle_path, "w") as f:
        json.dump(asdict(bundle), f, indent=2, default=str)
    
    return bundle_path


def load_replay_bundle(bundle_path: str) -> AttemptReplayBundle:
    """Load a replay bundle from disk.
    
    Args:
        bundle_path: Path to the bundle JSON file.
    
    Returns:
        Loaded AttemptReplayBundle.
    """
    with open(bundle_path) as f:
        data = json.load(f)
    
    # Reconstruct nested dataclasses
    data["environment"] = EnvironmentSnapshot(**data.get("environment", {}))
    
    if data.get("baseline_test"):
        data["baseline_test"] = TestExecution(**data["baseline_test"])
    if data.get("attempt_test"):
        data["attempt_test"] = TestExecution(**data["attempt_test"])
    
    return AttemptReplayBundle(**data)


def _get_controller_version() -> str:
    """Get the controller version string."""
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "unknown"


class ReplayRunner:
    """Execute replay of an attempt bundle."""
    
    def __init__(self, bundle: AttemptReplayBundle):
        """Initialize replay runner.
        
        Args:
            bundle: The replay bundle to execute.
        """
        self.bundle = bundle
    
    def verify_environment(self) -> Dict[str, Any]:
        """Verify current environment matches bundle.
        
        Returns:
            Dictionary with verification results.
        """
        import sys
        
        mismatches = []
        
        # Check Python version
        current_py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if current_py != self.bundle.environment.python_version:
            mismatches.append({
                "field": "python_version",
                "expected": self.bundle.environment.python_version,
                "actual": current_py,
            })
        
        # Check git revision
        if self.bundle.environment.git_revision:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=self.bundle.repo_path,
                    timeout=10,
                )
                if result.returncode == 0:
                    current_rev = result.stdout.strip()
                    if current_rev != self.bundle.environment.git_revision:
                        mismatches.append({
                            "field": "git_revision",
                            "expected": self.bundle.environment.git_revision,
                            "actual": current_rev,
                        })
            except Exception as e:
                mismatches.append({
                    "field": "git_revision",
                    "error": str(e),
                })
        
        return {
            "matches": len(mismatches) == 0,
            "mismatches": mismatches,
        }
    
    def replay(self, *, apply_patch: bool = True) -> TestExecution:
        """Replay the attempt.
        
        Args:
            apply_patch: Whether to apply the patch before running tests.
        
        Returns:
            TestExecution result from replay.
        """
        import time
        
        # Apply patch if requested
        if apply_patch and self.bundle.patch_diff:
            proc = subprocess.run(
                ["git", "apply", "-"],
                input=self.bundle.patch_diff,
                capture_output=True,
                text=True,
                cwd=self.bundle.repo_path,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Failed to apply patch: {proc.stderr}")
        
        # Run test command
        start = time.time()
        result = subprocess.run(
            self.bundle.test_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=self.bundle.repo_path,
            timeout=300,
        )
        duration_ms = int((time.time() - start) * 1000)
        
        return TestExecution(
            command=self.bundle.test_command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
    
    def compare_results(self, replay_result: TestExecution) -> Dict[str, Any]:
        """Compare replay result with original.
        
        Args:
            replay_result: Result from replay execution.
        
        Returns:
            Comparison dictionary.
        """
        original = self.bundle.attempt_test
        if not original:
            return {"error": "No original test execution in bundle"}
        
        return {
            "exit_code_match": replay_result.exit_code == original.exit_code,
            "original_exit_code": original.exit_code,
            "replay_exit_code": replay_result.exit_code,
            "duration_diff_ms": replay_result.duration_ms - original.duration_ms,
            "stdout_match": replay_result.stdout.strip() == original.stdout.strip(),
        }
