import subprocess
import tempfile
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.runtime.models import ExecutionRequest, ExecutionResult, RunStatus, WorkflowCapability, WorkflowMode
from src.runtime.registry import RunRegistry
from src.runtime.scheduler import ExecutionScheduler


def _git(repository_path: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=repository_path, check=True, capture_output=True, text=True)


class TestRuntimeScheduler(unittest.IsolatedAsyncioTestCase):
    async def test_submit_and_dispatch_active_task(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")
            revision = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            registry = RunRegistry(db_path=Path(tmp_dir) / "scheduler.db")
            scheduler = ExecutionScheduler(registry=registry)
            request = scheduler.submit_active_task(
                repository_path=repo_path,
                repository_revision=revision,
                payload={"task": "refactor"},
                metadata={"source": "test"},
            )

            fetched = registry.get_run(request.run_id)
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.status.value, "queued")

            fake_result = ExecutionResult(
                run_id=request.run_id,
                success=True,
                started_at=datetime(2026, 5, 27, 12, 1, tzinfo=timezone.utc),
                completed_at=datetime(2026, 5, 27, 12, 2, tzinfo=timezone.utc),
                artifacts={"workflow_output": {"ok": True}},
                metadata={"repository_revision": revision},
            )

            with patch.object(scheduler.executor, "execute", new=AsyncMock(return_value=fake_result)) as mock_execute:
                result = await scheduler.dispatch_next_mutation()

            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result, fake_result)
            fetched2 = registry.get_run(request.run_id)
            self.assertIsNotNone(fetched2)
            assert fetched2 is not None
            self.assertEqual(fetched2.status.value, "completed")
            self.assertEqual(scheduler.mutation_queue.active_run_id, None)
            mock_execute.assert_awaited_once()

    async def test_cleanup_stale_runs_marks_failure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")
            revision = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            registry = RunRegistry(db_path=Path(tmp_dir) / "scheduler.db")
            scheduler = ExecutionScheduler(registry=registry, stale_timeout_seconds=1)
            request = ExecutionRequest(
                run_id="run-stale",
                workflow_mode=WorkflowMode.ACTIVE,
                workflow_capability=WorkflowCapability.MUTATING,
                trigger="manual",
                repository_path=repo_path,
                repository_revision=revision,
                created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
                payload={"task": "refactor"},
                metadata={},
            )
            registry.create_run(request)
            registry.update_status(request.run_id, RunStatus.RUNNING, started_at=datetime.now(timezone.utc) - timedelta(seconds=3600))

            stale_ids = scheduler.cleanup_stale_runs()
            self.assertEqual(stale_ids, ["run-stale"])
            fetched = registry.get_run("run-stale")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.status.value, "failed")

    async def test_cancel_queued_run_removes_it_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")
            revision = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            registry = RunRegistry(db_path=Path(tmp_dir) / "scheduler.db")
            scheduler = ExecutionScheduler(registry=registry)
            request = scheduler.submit_active_task(
                repository_path=repo_path,
                repository_revision=revision,
                payload={"task": "refactor"},
                metadata={"source": "test"},
            )

            self.assertTrue(scheduler.cancel_run(request.run_id))
            self.assertEqual(scheduler.mutation_queue.remove(request.run_id), False)
            cancelled = registry.get_run(request.run_id)
            self.assertIsNotNone(cancelled)
            assert cancelled is not None
            self.assertEqual(cancelled.status.value, "cancelled")

            result = await scheduler.dispatch_next_mutation()
            self.assertIsNone(result)

    async def test_cancel_running_run_is_observed_cooperatively(self):
        with tempfile.TemporaryDirectory() as tmp_dir, tempfile.TemporaryDirectory() as db_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")
            revision = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            registry = RunRegistry(db_path=Path(db_dir) / "scheduler.db")
            scheduler = ExecutionScheduler(registry=registry)
            request = scheduler.submit_active_task(
                repository_path=repo_path,
                repository_revision=revision,
                payload={"task": "refactor"},
                metadata={"source": "test"},
            )

            async def fake_file_reader_node(state, run_context):
                await asyncio.sleep(0.05)
                return {"original_code": "hello", "target_file": str(tracked)}

            with patch("src.graph.nodes.nodes.file_reader_node", side_effect=fake_file_reader_node):
                cancellation_task = asyncio.create_task(asyncio.sleep(0.01))

                async def cancel_after_delay():
                    await cancellation_task
                    scheduler.cancel_run(request.run_id)

                cancel_task = asyncio.create_task(cancel_after_delay())
                result = await scheduler.dispatch_next_mutation()
                await cancel_task

            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(result.cancelled)
            cancelled = registry.get_run(request.run_id)
            self.assertIsNotNone(cancelled)
            assert cancelled is not None
            self.assertEqual(cancelled.status.value, "cancelled")

    async def test_cancel_completed_run_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")
            revision = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            registry = RunRegistry(db_path=Path(tmp_dir) / "scheduler.db")
            scheduler = ExecutionScheduler(registry=registry)
            request = scheduler.submit_active_task(
                repository_path=repo_path,
                repository_revision=revision,
                payload={"task": "refactor"},
                metadata={"source": "test"},
            )

            fake_result = ExecutionResult(
                run_id=request.run_id,
                success=True,
                started_at=datetime(2026, 5, 27, 12, 1, tzinfo=timezone.utc),
                completed_at=datetime(2026, 5, 27, 12, 2, tzinfo=timezone.utc),
                artifacts={"workflow_output": {"ok": True}},
                metadata={"repository_revision": revision},
            )

            with patch.object(scheduler.executor, "execute", new=AsyncMock(return_value=fake_result)):
                result = await scheduler.dispatch_next_mutation()

            self.assertEqual(result, fake_result)
            completed = registry.get_run(request.run_id)
            self.assertIsNotNone(completed)
            assert completed is not None
            self.assertEqual(completed.status.value, "completed")
            self.assertFalse(scheduler.cancel_run(request.run_id))
            completed_again = registry.get_run(request.run_id)
            self.assertIsNotNone(completed_again)
            assert completed_again is not None
            self.assertEqual(completed_again.status.value, "completed")
