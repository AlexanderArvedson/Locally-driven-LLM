import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.runtime.models import ExecutionRequest, RunStatus, WorkflowCapability, WorkflowMode
from src.runtime.registry import RunRegistry


class TestRuntimeRegistry(unittest.TestCase):
    def test_create_update_and_query_runs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "scheduler.db"
            registry = RunRegistry(db_path=db_path)
            request = ExecutionRequest(
                run_id="run-1",
                workflow_mode=WorkflowMode.ACTIVE,
                workflow_capability=WorkflowCapability.MUTATING,
                trigger="manual",
                repository_path=Path(tmp_dir),
                repository_revision="abc123",
                created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
                payload={"task": "refactor"},
                metadata={"source": "test"},
            )

            created = registry.create_run(request)
            self.assertEqual(created.status, RunStatus.PENDING)

            queued = registry.update_status(
                "run-1",
                RunStatus.QUEUED,
                queued_at=datetime(2026, 5, 27, 12, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(queued.status, RunStatus.QUEUED)
            self.assertEqual(queued.queued_at, datetime(2026, 5, 27, 12, 1, tzinfo=timezone.utc))

            running = registry.update_status(
                "run-1",
                RunStatus.RUNNING,
                started_at=datetime(2026, 5, 27, 12, 2, tzinfo=timezone.utc),
            )
            self.assertEqual(running.status, RunStatus.RUNNING)
            self.assertEqual(running.started_at, datetime(2026, 5, 27, 12, 2, tzinfo=timezone.utc))

            active_runs = registry.list_active_runs()
            self.assertEqual([record.run_id for record in active_runs], ["run-1"])

            fetched = registry.get_run("run-1")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.run_id, "run-1")
            self.assertEqual(fetched.payload, {"task": "refactor"})

    def test_stale_run_detection_uses_start_time(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "scheduler.db"
            registry = RunRegistry(db_path=db_path)
            request = ExecutionRequest(
                run_id="run-2",
                workflow_mode=WorkflowMode.PASSIVE,
                workflow_capability=WorkflowCapability.READ_ONLY,
                trigger="scheduled",
                repository_path=Path(tmp_dir),
                repository_revision="abc123",
                created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
                payload={"task": "scan"},
                metadata={},
            )

            registry.create_run(request)
            registry.update_status(
                "run-2",
                RunStatus.RUNNING,
                started_at=datetime.now(timezone.utc) - timedelta(seconds=3600),
            )

            stale_runs = registry.find_stale_runs(timeout_seconds=300)
            self.assertEqual([record.run_id for record in stale_runs], ["run-2"])
