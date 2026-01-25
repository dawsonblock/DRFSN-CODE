"""CLI for replay bundle operations.

Provides subcommands for:
- replay run <bundle.json>: Replay an attempt from a bundle
- replay verify <bundle.json>: Verify environment matches bundle
- replay list <dir>: List available replay bundles
"""

import argparse
import json
import os
import sys
from typing import Optional


def cmd_replay_run(args: argparse.Namespace) -> int:
    """Run a replay from a bundle file.
    
    Args:
        args: Parsed arguments with bundle_path, no_patch options.
    
    Returns:
        Exit code (0 on success).
    """
    from .replay_bundle import ReplayRunner, load_replay_bundle
    
    bundle_path = args.bundle
    if not os.path.exists(bundle_path):
        print(f"Error: Bundle file not found: {bundle_path}", file=sys.stderr)
        return 1
    
    print(f"Loading bundle: {bundle_path}")
    bundle = load_replay_bundle(bundle_path)
    
    print(f"Bundle ID: {bundle.bundle_id}")
    print(f"Run ID: {bundle.run_id}")
    print(f"Step: {bundle.step_number}")
    print(f"Created: {bundle.created_at}")
    print()
    
    runner = ReplayRunner(bundle)
    
    # Verify environment
    print("Verifying environment...")
    verification = runner.verify_environment()
    
    if not verification["matches"]:
        print("⚠️  Environment mismatches detected:")
        for mismatch in verification["mismatches"]:
            print(f"  - {mismatch['field']}: expected={mismatch.get('expected')}, actual={mismatch.get('actual')}")
        print()
        
        if not args.force:
            print("Use --force to continue despite mismatches.")
            return 1
    else:
        print("✅ Environment matches bundle")
    
    # Run replay
    print()
    print("Running replay...")
    apply_patch = not args.no_patch
    
    try:
        result = runner.replay(apply_patch=apply_patch)
    except Exception as e:
        print(f"❌ Replay failed: {e}", file=sys.stderr)
        return 1
    
    print()
    print(f"Exit code: {result.exit_code}")
    print(f"Duration: {result.duration_ms}ms")
    
    # Compare with original if available
    if bundle.attempt_test:
        comparison = runner.compare_results(result)
        print()
        if comparison.get("exit_code_match"):
            print("✅ Exit code matches original")
        else:
            print(f"⚠️  Exit code differs: original={comparison['original_exit_code']}, replay={comparison['replay_exit_code']}")
    
    if args.verbose:
        print()
        print("=== STDOUT ===")
        print(result.stdout[:2000] if len(result.stdout) > 2000 else result.stdout)
        print()
        print("=== STDERR ===")
        print(result.stderr[:2000] if len(result.stderr) > 2000 else result.stderr)
    
    return 0 if result.exit_code == 0 else 1


def cmd_replay_verify(args: argparse.Namespace) -> int:
    """Verify environment matches a bundle.
    
    Args:
        args: Parsed arguments with bundle_path.
    
    Returns:
        Exit code (0 if matches, 1 if mismatches).
    """
    from .replay_bundle import ReplayRunner, load_replay_bundle
    
    bundle_path = args.bundle
    if not os.path.exists(bundle_path):
        print(f"Error: Bundle file not found: {bundle_path}", file=sys.stderr)
        return 1
    
    bundle = load_replay_bundle(bundle_path)
    runner = ReplayRunner(bundle)
    
    verification = runner.verify_environment()
    
    print(f"Bundle: {bundle.bundle_id}")
    print(f"Git revision: {bundle.environment.git_revision[:12] if bundle.environment.git_revision else 'N/A'}")
    print(f"Python version: {bundle.environment.python_version}")
    print()
    
    if verification["matches"]:
        print("✅ Environment matches bundle")
        return 0
    else:
        print("❌ Environment mismatches:")
        for mismatch in verification["mismatches"]:
            field = mismatch["field"]
            expected = mismatch.get("expected", "N/A")
            actual = mismatch.get("actual", "N/A")
            print(f"  {field}:")
            print(f"    Expected: {expected}")
            print(f"    Actual:   {actual}")
        return 1


def cmd_replay_list(args: argparse.Namespace) -> int:
    """List available replay bundles in a directory.
    
    Args:
        args: Parsed arguments with directory path.
    
    Returns:
        Exit code (0 on success).
    """
    from .replay_bundle import load_replay_bundle
    
    search_dir = args.directory or "."
    
    bundles = []
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if fname.startswith("replay_") and fname.endswith(".json"):
                bundles.append(os.path.join(root, fname))
    
    if not bundles:
        print(f"No replay bundles found in {search_dir}")
        return 0
    
    print(f"Found {len(bundles)} replay bundle(s):\n")
    
    for bundle_path in sorted(bundles):
        try:
            bundle = load_replay_bundle(bundle_path)
            status = "✓" if bundle.attempt_test and bundle.attempt_test.exit_code == 0 else "✗"
            print(f"  {status} {bundle.bundle_id[:8]}  step={bundle.step_number:2d}  {bundle.created_at[:10]}  {os.path.basename(bundle_path)}")
        except Exception as e:
            print(f"  ? {os.path.basename(bundle_path)} (error: {e})")
    
    return 0


def cmd_replay_show(args: argparse.Namespace) -> int:
    """Show details of a replay bundle.
    
    Args:
        args: Parsed arguments with bundle_path.
    
    Returns:
        Exit code (0 on success).
    """
    from .replay_bundle import load_replay_bundle
    
    bundle_path = args.bundle
    if not os.path.exists(bundle_path):
        print(f"Error: Bundle file not found: {bundle_path}", file=sys.stderr)
        return 1
    
    bundle = load_replay_bundle(bundle_path)
    
    print("═" * 60)
    print(f" Replay Bundle: {bundle.bundle_id}")
    print("═" * 60)
    print()
    print(f"Run ID:          {bundle.run_id}")
    print(f"Step Number:     {bundle.step_number}")
    print(f"Created:         {bundle.created_at}")
    print(f"Controller:      {bundle.controller_version}")
    print()
    print("─ Environment ─")
    print(f"  Python:        {bundle.environment.python_version}")
    print(f"  Git Revision:  {bundle.environment.git_revision[:12] if bundle.environment.git_revision else 'N/A'}")
    print(f"  Git Branch:    {bundle.environment.git_branch}")
    print(f"  Git Dirty:     {bundle.environment.git_dirty}")
    print(f"  Docker Image:  {bundle.environment.docker_image or 'N/A'}")
    print(f"  Packages:      {len(bundle.environment.pip_freeze)} installed")
    print()
    print("─ Attempt ─")
    print(f"  Test Command:  {bundle.test_command}")
    print(f"  Patch Hash:    {bundle.patch_hash}")
    print(f"  Patch Lines:   {len(bundle.patch_diff.splitlines()) if bundle.patch_diff else 0}")
    
    if bundle.baseline_test:
        print()
        print("─ Baseline Test ─")
        print(f"  Exit Code:     {bundle.baseline_test.exit_code}")
        print(f"  Duration:      {bundle.baseline_test.duration_ms}ms")
    
    if bundle.attempt_test:
        print()
        print("─ Attempt Test ─")
        print(f"  Exit Code:     {bundle.attempt_test.exit_code}")
        print(f"  Duration:      {bundle.attempt_test.duration_ms}ms")
    
    if args.show_patch and bundle.patch_diff:
        print()
        print("─ Patch ─")
        print(bundle.patch_diff[:3000])
        if len(bundle.patch_diff) > 3000:
            print(f"... ({len(bundle.patch_diff) - 3000} more characters)")
    
    return 0


def create_replay_parser() -> argparse.ArgumentParser:
    """Create the replay CLI argument parser.
    
    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="rfsn replay",
        description="Replay bundle operations for deterministic debugging",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Replay commands")
    
    # replay run
    run_parser = subparsers.add_parser("run", help="Run a replay from a bundle")
    run_parser.add_argument("bundle", help="Path to replay bundle JSON file")
    run_parser.add_argument("--no-patch", action="store_true", help="Run without applying the patch")
    run_parser.add_argument("--force", action="store_true", help="Continue despite environment mismatches")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Show stdout/stderr output")
    run_parser.set_defaults(func=cmd_replay_run)
    
    # replay verify
    verify_parser = subparsers.add_parser("verify", help="Verify environment matches bundle")
    verify_parser.add_argument("bundle", help="Path to replay bundle JSON file")
    verify_parser.set_defaults(func=cmd_replay_verify)
    
    # replay list
    list_parser = subparsers.add_parser("list", help="List available replay bundles")
    list_parser.add_argument("directory", nargs="?", default=".", help="Directory to search")
    list_parser.set_defaults(func=cmd_replay_list)
    
    # replay show
    show_parser = subparsers.add_parser("show", help="Show bundle details")
    show_parser.add_argument("bundle", help="Path to replay bundle JSON file")
    show_parser.add_argument("--show-patch", action="store_true", help="Include patch content")
    show_parser.set_defaults(func=cmd_replay_show)
    
    return parser


def replay_main(args: Optional[list] = None) -> int:
    """Entry point for replay CLI.
    
    Args:
        args: Optional argument list (uses sys.argv if None).
    
    Returns:
        Exit code.
    """
    parser = create_replay_parser()
    parsed = parser.parse_args(args)
    
    if not parsed.command:
        parser.print_help()
        return 1
    
    return parsed.func(parsed)


if __name__ == "__main__":
    sys.exit(replay_main())
