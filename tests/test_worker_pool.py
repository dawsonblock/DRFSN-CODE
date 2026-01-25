"""Unit tests for worker pool and task DAG."""

import pytest


class TestWorkerPatchProposal:
    """Tests for WorkerPatchProposal."""

    def test_proposal_hash(self):
        """Proposal hash is deterministic."""
        from rfsn_controller.worker_pool import WorkerPatchProposal

        p1 = WorkerPatchProposal(
            worker_id="w1", task_id="t1", proposal_id="p1",
            diff="--- a/f.py\n+++ b/f.py", confidence=0.8,
        )
        p2 = WorkerPatchProposal(
            worker_id="w2", task_id="t2", proposal_id="p2",
            diff="--- a/f.py\n+++ b/f.py", confidence=0.5,
        )
        # Same diff = same hash
        assert p1.proposal_hash() == p2.proposal_hash()

    def test_proposal_as_dict(self):
        """Proposal can be converted to dict."""
        from rfsn_controller.worker_pool import WorkerPatchProposal

        p = WorkerPatchProposal(
            worker_id="w1", task_id="t1", proposal_id="p1",
            diff="diff", confidence=0.9,
        )
        d = p.as_dict()
        assert d["worker_id"] == "w1"
        assert d["confidence"] == 0.9


class TestTaskDAG:
    """Tests for task DAG."""

    def test_add_task(self):
        """Tasks can be added to DAG."""
        from rfsn_controller.worker_pool import TaskDAG

        dag = TaskDAG()
        task = dag.add_task("t1", "Do something")
        assert "t1" in dag.tasks
        assert task.description == "Do something"

    def test_dependency_tracking(self):
        """Dependencies are tracked correctly."""
        from rfsn_controller.worker_pool import TaskDAG

        dag = TaskDAG()
        dag.add_task("t1", "First")
        dag.add_task("t2", "Second", dependencies=["t1"])

        # t1 has no dependencies, t2 depends on t1
        assert dag.tasks["t1"].dependencies == []
        assert dag.tasks["t2"].dependencies == ["t1"]
        assert "t2" in dag.tasks["t1"].dependents

    def test_ready_tasks(self):
        """Ready tasks have satisfied dependencies."""
        from rfsn_controller.worker_pool import TaskDAG

        dag = TaskDAG()
        dag.add_task("t1", "First")
        dag.add_task("t2", "Second", dependencies=["t1"])

        # Only t1 is ready initially
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

        # After completing t1, t2 becomes ready
        dag.mark_completed("t1")
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t2"

    def test_execution_order(self):
        """Topological order respects dependencies."""
        from rfsn_controller.worker_pool import TaskDAG

        dag = TaskDAG()
        dag.add_task("a", "A")
        dag.add_task("b", "B", dependencies=["a"])
        dag.add_task("c", "C", dependencies=["a"])
        dag.add_task("d", "D", dependencies=["b", "c"])

        order = dag.get_execution_order()
        # a must come first, d must come last
        assert order[0] == "a"
        assert order[-1] == "d"
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")


class TestConflictResolver:
    """Tests for conflict resolution."""

    def test_highest_confidence(self):
        """Highest confidence proposal wins."""
        from rfsn_controller.worker_pool import (
            ConflictResolution,
            ConflictResolver,
            WorkerPatchProposal,
        )

        resolver = ConflictResolver(ConflictResolution.HIGHEST_CONFIDENCE)
        
        low = WorkerPatchProposal("w1", "t1", "p1", "diff1", 0.3)
        mid = WorkerPatchProposal("w2", "t1", "p2", "diff2", 0.6)
        high = WorkerPatchProposal("w3", "t1", "p3", "diff3", 0.9)

        result = resolver.resolve([low, mid, high])
        assert result.proposal_id == "p3"

    def test_first_wins(self):
        """First proposal wins with FIRST_WINS strategy."""
        from rfsn_controller.worker_pool import (
            ConflictResolution,
            ConflictResolver,
            WorkerPatchProposal,
        )

        resolver = ConflictResolver(ConflictResolution.FIRST_WINS)
        
        p1 = WorkerPatchProposal("w1", "t1", "p1", "diff1", 0.3)
        p2 = WorkerPatchProposal("w2", "t1", "p2", "diff2", 0.9)

        result = resolver.resolve([p1, p2])
        assert result.proposal_id == "p1"

    def test_empty_diff_filtered(self):
        """Empty diffs are filtered out."""
        from rfsn_controller.worker_pool import (
            ConflictResolver,
            WorkerPatchProposal,
        )

        resolver = ConflictResolver()
        
        empty = WorkerPatchProposal("w1", "t1", "p1", "", 0.9)
        valid = WorkerPatchProposal("w2", "t1", "p2", "real diff", 0.5)

        result = resolver.resolve([empty, valid])
        assert result.proposal_id == "p2"


class TestWorkerPool:
    """Tests for WorkerPool."""

    def test_add_remove_worker(self):
        """Workers can be added and removed."""
        from rfsn_controller.worker_pool import SimpleWorkerAgent, WorkerPool

        pool = WorkerPool()
        worker = SimpleWorkerAgent("w1", lambda t: [("diff", 0.8)])
        
        pool.add_worker(worker)
        assert "w1" in pool.workers
        
        pool.remove_worker("w1")
        assert "w1" not in pool.workers

    def test_process_task_collects_proposals(self):
        """Pool collects proposals from all workers."""
        from rfsn_controller.worker_pool import (
            SimpleWorkerAgent,
            TaskNode,
            WorkerPool,
        )

        w1 = SimpleWorkerAgent("w1", lambda t: [("diff1", 0.5)])
        w2 = SimpleWorkerAgent("w2", lambda t: [("diff2", 0.8)])
        pool = WorkerPool(workers=[w1, w2])

        task = TaskNode("t1", "Do something")
        result = pool.process_task(task)

        # Should have proposals from both workers
        assert len(task.proposals) == 2
        # Should select highest confidence
        assert result.confidence == 0.8


class TestDecomposeTask:
    """Tests for task decomposition."""

    def test_single_file_single_task(self):
        """Single test file creates single task."""
        from rfsn_controller.worker_pool import decompose_task

        dag = decompose_task(
            "Fix the bug",
            failing_tests=["tests/test_foo.py::test_bar"],
            error_signatures=["AssertionError"],
        )
        assert len(dag.tasks) == 1
        assert "fix_all" in dag.tasks

    def test_multi_file_creates_subtasks(self):
        """Multiple test files create subtasks + integration."""
        from rfsn_controller.worker_pool import decompose_task

        dag = decompose_task(
            "Fix multiple bugs",
            failing_tests=[
                "tests/test_a.py::test_1",
                "tests/test_b.py::test_2",
            ],
            error_signatures=["Error1", "Error2"],
        )
        # Should have 2 subtasks + 1 integration task
        assert len(dag.tasks) == 3
        assert "integrate" in dag.tasks
        # Integration depends on both subtasks
        assert len(dag.tasks["integrate"].dependencies) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
