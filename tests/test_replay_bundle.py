"""Unit tests for replay bundle functionality."""

import json
import os
import tempfile

import pytest


class TestAttemptReplayBundle:
    """Tests for AttemptReplayBundle dataclass."""

    def test_create_replay_bundle(self):
        """Test creating a replay bundle captures required fields."""
        from rfsn_controller.replay_bundle import create_replay_bundle

        bundle = create_replay_bundle(
            run_id="test-run-123",
            step_number=5,
            repo_path="/tmp/test-repo",
            test_command="pytest -q",
            patch_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-x=1\n+x=2",
        )

        assert bundle.run_id == "test-run-123"
        assert bundle.step_number == 5
        assert bundle.test_command == "pytest -q"
        assert len(bundle.bundle_id) == 16  # SHA256 truncated
        assert bundle.patch_hash  # Should have computed hash

    def test_bundle_export_and_load(self):
        """Test exporting and loading a bundle preserves data."""
        from rfsn_controller.replay_bundle import (
            AttemptReplayBundle,
            EnvironmentSnapshot,
            export_replay_bundle,
            load_replay_bundle,
        )

        original = AttemptReplayBundle(
            bundle_id="abc123",
            run_id="test-run",
            created_at="2024-01-01T00:00:00Z",
            environment=EnvironmentSnapshot(
                python_version="3.11.0",
                git_revision="abc123def456",
            ),
            test_command="pytest",
            step_number=1,
            patch_diff="test diff",
            patch_hash="hash123",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_replay_bundle(original, tmpdir)
            assert os.path.exists(path)

            loaded = load_replay_bundle(path)
            assert loaded.bundle_id == original.bundle_id
            assert loaded.run_id == original.run_id
            assert loaded.test_command == original.test_command
            assert loaded.environment.python_version == "3.11.0"


class TestEnvironmentSnapshot:
    """Tests for environment capture."""

    def test_capture_environment_basic(self):
        """Test basic environment capture."""
        from rfsn_controller.replay_bundle import capture_environment

        with tempfile.TemporaryDirectory() as tmpdir:
            env = capture_environment(repo_path=tmpdir)

            assert env.python_version  # Should capture version
            # May or may not have git info depending on if it's a repo


class TestReplayRunner:
    """Tests for ReplayRunner."""

    def test_verify_environment_python_version(self):
        """Test environment verification checks Python version."""
        import sys
        from rfsn_controller.replay_bundle import (
            AttemptReplayBundle,
            EnvironmentSnapshot,
            ReplayRunner,
        )

        # Create bundle with current Python version (should match)
        current_py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        bundle = AttemptReplayBundle(
            bundle_id="test",
            run_id="test-run",
            created_at="2024-01-01T00:00:00Z",
            environment=EnvironmentSnapshot(python_version=current_py),
            repo_path="/tmp",
            test_command="true",
        )

        runner = ReplayRunner(bundle)
        result = runner.verify_environment()

        # Python version should match
        python_mismatches = [m for m in result["mismatches"] if m["field"] == "python_version"]
        assert len(python_mismatches) == 0

    def test_verify_environment_detects_mismatch(self):
        """Test that version mismatches are detected."""
        from rfsn_controller.replay_bundle import (
            AttemptReplayBundle,
            EnvironmentSnapshot,
            ReplayRunner,
        )

        # Create bundle with wrong Python version
        bundle = AttemptReplayBundle(
            bundle_id="test",
            run_id="test-run",
            created_at="2024-01-01T00:00:00Z",
            environment=EnvironmentSnapshot(python_version="2.7.18"),  # Wrong version
            repo_path="/tmp",
            test_command="true",
        )

        runner = ReplayRunner(bundle)
        result = runner.verify_environment()

        assert not result["matches"]
        assert any(m["field"] == "python_version" for m in result["mismatches"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
