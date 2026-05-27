import subprocess
import tempfile
import unittest
import unittest.mock as mock
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.runtime.executor import WorkflowExecutor
from src.runtime.models import ExecutionRequest, WorkflowCapability, WorkflowMode


def _git(repository_path: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=repository_path, check=True, capture_output=True, text=True)


class TestRuntimeExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_execute_returns_success_result(self):
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

            request = ExecutionRequest(
                run_id="run-1",
                workflow_mode=WorkflowMode.ACTIVE,
                workflow_capability=WorkflowCapability.MUTATING,
                trigger="manual",
                repository_path=repo_path,
                repository_revision=revision,
                created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
                payload={"task": "refactor"},
                metadata={"source": "test"},
            )

            fake_graph = mock.Mock()
            fake_graph.ainvoke = AsyncMock(return_value={"ok": True})

            with patch("src.runtime.executor.make_graph", return_value=fake_graph) as mock_make_graph:
                executor = WorkflowExecutor(timeout_seconds=10)
                result = await executor.execute(request)

            self.assertTrue(result.success)
            self.assertEqual(result.artifacts, {"workflow_output": {"ok": True}})
            self.assertEqual(result.metadata["repository_revision"], revision)
            fake_graph.ainvoke.assert_awaited_with({"task": "refactor"})
            mock_make_graph.assert_called_once()

    async def test_execute_restores_repository_on_failure(self):
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

            request = ExecutionRequest(
                run_id="run-2",
                workflow_mode=WorkflowMode.PASSIVE,
                workflow_capability=WorkflowCapability.READ_ONLY,
                trigger="scheduled",
                repository_path=repo_path,
                repository_revision=revision,
                created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
                payload={"task": "scan"},
                metadata={},
            )

            fake_graph = mock.Mock()
            fake_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

            with patch("src.runtime.executor.make_graph", return_value=fake_graph), patch(
                "src.runtime.executor.restore_repository_state"
            ) as mock_restore:
                executor = WorkflowExecutor(timeout_seconds=10)
                result = await executor.execute(request)

            self.assertFalse(result.success)
            self.assertEqual(result.error, "boom")
            mock_restore.assert_called_once_with(repo_path)
