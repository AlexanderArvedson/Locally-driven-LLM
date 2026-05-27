import subprocess
import tempfile
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

            self.assertEqual(registry.get_run(request.run_id).status.value, "queued")

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

            self.assertEqual(result, fake_result)
            self.assertEqual(registry.get_run(request.run_id).status.value, "completed")
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
            self.assertEqual(registry.get_run("run-stale").status.value, "failed")
