import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.runtime.models import (
    ExecutionRequest,
    ExecutionResult,
    RunStatus,
    WorkflowCapability,
    WorkflowMode,
)


class TestRuntimeModels(unittest.TestCase):
    def test_enums_are_stable(self):
        self.assertEqual(RunStatus.PENDING.value, "pending")
        self.assertEqual(RunStatus.CANCELLED.value, "cancelled")
        self.assertEqual(WorkflowMode.PASSIVE.value, "passive")
        self.assertEqual(WorkflowCapability.MUTATING.value, "mutating")

    def test_request_and_result_are_serializable(self):
        request = ExecutionRequest(
            run_id="run-1",
            workflow_mode=WorkflowMode.ACTIVE,
            workflow_capability=WorkflowCapability.MUTATING,
            trigger="manual",
            repository_path=Path("/tmp/repo"),
            repository_revision="abc123",
            created_at=datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc),
            payload={"task": "refactor"},
            metadata={"source": "test"},
        )

        result = ExecutionResult(
            run_id="run-1",
            success=True,
            started_at=datetime(2026, 5, 27, 12, 1, tzinfo=timezone.utc),
            completed_at=datetime(2026, 5, 27, 12, 2, tzinfo=timezone.utc),
            artifacts={"files": 1},
            metadata={"source": "test"},
        )

        request_data = request.to_dict()
        result_data = result.to_dict()

        self.assertEqual(request_data["workflow_mode"], "active")
        self.assertEqual(request_data["workflow_capability"], "mutating")
        self.assertEqual(request_data["repository_path"], "/tmp/repo")
        self.assertEqual(request_data["created_at"], "2026-05-27T12:00:00+00:00")
        self.assertEqual(result_data["started_at"], "2026-05-27T12:01:00+00:00")
        self.assertEqual(result_data["completed_at"], "2026-05-27T12:02:00+00:00")
