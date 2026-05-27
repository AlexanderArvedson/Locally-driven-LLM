import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.runtime.models import ExecutionRequest, WorkflowCapability, WorkflowMode
from src.runtime.queue import MutationQueue


class TestRuntimeQueue(unittest.TestCase):
    def test_fifo_order_and_active_gate(self):
        queue = MutationQueue()
        first = ExecutionRequest(
            run_id="run-1",
            workflow_mode=WorkflowMode.ACTIVE,
            workflow_capability=WorkflowCapability.MUTATING,
            trigger="manual",
            repository_path=Path("/tmp/repo"),
            repository_revision="abc123",
            created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
            payload={"task": "first"},
            metadata={},
        )
        second = ExecutionRequest(
            run_id="run-2",
            workflow_mode=WorkflowMode.ACTIVE,
            workflow_capability=WorkflowCapability.MUTATING,
            trigger="manual",
            repository_path=Path("/tmp/repo"),
            repository_revision="abc123",
            created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
            payload={"task": "second"},
            metadata={},
        )

        queue.enqueue(first)
        queue.enqueue(second)

        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.dequeue(), first)
        queue.mark_active("run-1")
        self.assertTrue(queue.has_active_mutation())
        self.assertIsNone(queue.dequeue())
        queue.clear_active("run-1")
        self.assertEqual(queue.dequeue(), second)

    def test_rejects_read_only_requests_and_multiple_active_runs(self):
        queue = MutationQueue()
        read_only = ExecutionRequest(
            run_id="run-3",
            workflow_mode=WorkflowMode.PASSIVE,
            workflow_capability=WorkflowCapability.READ_ONLY,
            trigger="scheduled",
            repository_path=Path("/tmp/repo"),
            repository_revision="abc123",
            created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
            payload={"task": "scan"},
            metadata={},
        )

        with self.assertRaises(ValueError):
            queue.enqueue(read_only)

        queue.mark_active("run-1")
        with self.assertRaises(RuntimeError):
            queue.mark_active("run-2")

    def test_remove_drops_queued_run_by_id(self):
        queue = MutationQueue()
        first = ExecutionRequest(
            run_id="run-1",
            workflow_mode=WorkflowMode.ACTIVE,
            workflow_capability=WorkflowCapability.MUTATING,
            trigger="manual",
            repository_path=Path("/tmp/repo"),
            repository_revision="abc123",
            created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
            payload={"task": "first"},
            metadata={},
        )
        second = ExecutionRequest(
            run_id="run-2",
            workflow_mode=WorkflowMode.ACTIVE,
            workflow_capability=WorkflowCapability.MUTATING,
            trigger="manual",
            repository_path=Path("/tmp/repo"),
            repository_revision="abc123",
            created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
            payload={"task": "second"},
            metadata={},
        )

        queue.enqueue(first)
        queue.enqueue(second)

        self.assertTrue(queue.remove("run-1"))
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.dequeue(), second)
