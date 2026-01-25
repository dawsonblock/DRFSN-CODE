"""CI Entrypoint - GitHub Action Integration.

Adapts the Controller to run within a CI environment (GitHub Actions).
Reads inputs from environment variables, executes the plan, and 
outputs results to GITHUB_OUTPUT and summary to GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Imports for future integration (stubs for now)
try:
    from .planner_v2.controller_adapter import ControllerAdapter  # noqa: F401
    from .planner_v2.schema import ControllerOutcome  # noqa: F401
    from .explainer import Explainer
except ImportError:
    # Allow import failure during setup
    Explainer = None  # type: ignore


def run_ci_job(
    goal: str,
    repo_path: str,
    github_token: Optional[str] = None,
) -> int:
    """Run the controller in CI mode.
    
    Args:
        goal: The goal to execute.
        repo_path: Path to the repository.
        github_token: Optional GitHub token.
        
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print("::group::Setup Controller")
    print(f"Goal: {goal}")
    print(f"Repo: {repo_path}")
    
    # Initialize adapter
    # mechanism to inject dependencies would go here
    print("Initializing components...")
    
    # Mocking execution for the skeleton
    # In real usage:
    # adapter = ControllerAdapter(...)
    # spec = adapter.start_goal(goal, context)
    # ... execution loop ...
    # summary_data = adapter.get_summary()
    
    # Generate explanation
    explainer = Explainer()
    # Mock data for demonstration
    summary_md = explainer.explain_plan(
        {"goal": goal, "is_complete": True, "total_steps": 1},
        [{"title": "Analyze", "intent": "Check code", "status": "DONE", "result": {"success": True}}]
    )
    
    success = True
    print("::endgroup::")
    
    # Write summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(summary_md)
            
    # Write outputs
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"success={'true' if success else 'false'}\n")
            
    return 0 if success else 1


if __name__ == "__main__":
    # Read inputs
    goal = os.environ.get("INPUT_GOAL", "Analyze and fix issues")
    repo = os.environ.get("GITHUB_WORKSPACE", ".")
    token = os.environ.get("INPUT_GITHUB_TOKEN")
    
    sys.exit(run_ci_job(goal, repo, token))
