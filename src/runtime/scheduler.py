"""Deterministic execution scheduler for Phase 3 orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4
from typing import Any

from src.runtime.executor import WorkflowExecutor
from src.runtime.models import (
    CancellationToken,
    ExecutionRequest,
    ExecutionResult,
    RunStatus,
    WorkflowCapability,
    WorkflowMode,
    utc_now,
)
from src.runtime.queue import MutationQueue
from src.runtime.registry import RunRegistry


@dataclass(slots=True)
class ExecutionScheduler:
    """Coordinate workflow execution without depending on LangGraph internals."""

    registry: RunRegistry = field(default_factory=RunRegistry)
    executor: WorkflowExecutor = field(default_factory=WorkflowExecutor)
    mutation_queue: MutationQueue = field(default_factory=MutationQueue)
    passive_interval_seconds: int = 300
    stale_timeout_seconds: int = 3600

    def submit_active_task(
        self,
        *,
        repository_path: Path,
        repository_revision: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        trigger: str = "manual",
    ) -> ExecutionRequest:
        """Create and queue a mutation workflow request."""

        request = ExecutionRequest(
            run_id=self._new_run_id(),
            workflow_mode=WorkflowMode.ACTIVE,
            workflow_capability=WorkflowCapability.MUTATING,
            trigger=trigger,
            repository_path=repository_path,
            repository_revision=repository_revision,
            created_at=utc_now(),
            payload=payload,
            metadata=metadata or {},
        )
        self.registry.create_run(request, status=RunStatus.PENDING)
        self.registry.update_status(request.run_id, RunStatus.QUEUED, queued_at=utc_now())
        self.mutation_queue.enqueue(request)
        return request

    def cancel_run(self, run_id: str) -> bool:
        """Request cooperative cancellation for a run.

        Queued runs are removed from the in-memory queue and marked cancelled
        in SQLite. Running runs are marked cancelled in SQLite so the executor
        can observe the request at its next checkpoint. Completed runs are a
        no-op and return False.
        """

        record = self.registry.get_run(run_id)
        if record is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        if record.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return False

        self.mutation_queue.remove(run_id)
        self.registry.mark_cancelled(run_id)
        return True

    def _build_cancellation_token(self, run_id: str) -> CancellationToken:
        return CancellationToken(run_id=run_id, is_cancelled=lambda: self._is_cancelled(run_id))

    def _is_cancelled(self, run_id: str) -> bool:
        record = self.registry.get_run(run_id)
        return record is not None and record.status == RunStatus.CANCELLED

    async def dispatch_next_mutation(self) -> ExecutionResult | None:
        """Dispatch the next queued mutation workflow if one is available."""

        if self.mutation_queue.has_active_mutation():
            return None

        request = self.mutation_queue.dequeue()
        if request is None:
            return None

        self.mutation_queue.mark_active(request.run_id)
        self.registry.update_status(request.run_id, RunStatus.RUNNING, started_at=utc_now())
        try:
            result = await self.executor.execute(request, cancellation_token=self._build_cancellation_token(request.run_id))
        finally:
            self.mutation_queue.clear_active(request.run_id)

        self.registry.record_result(result)
        return result

    async def execute_passive_task(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a passive workflow request immediately through the executor."""

        self.registry.create_run(request, status=RunStatus.PENDING)
        self.registry.update_status(request.run_id, RunStatus.RUNNING, started_at=utc_now())
        result = await self.executor.execute(request, cancellation_token=self._build_cancellation_token(request.run_id))
        self.registry.record_result(result)
        return result

    def cleanup_stale_runs(self) -> list[str]:
        """Mark stale running executions as failed in the registry."""

        stale_runs = self.registry.find_stale_runs(self.stale_timeout_seconds)
        stale_run_ids: list[str] = []
        for record in stale_runs:
            stale_run_ids.append(record.run_id)
            self.registry.record_failure(record.run_id, "stale run detected")
            if self.mutation_queue.active_run_id == record.run_id:
                self.mutation_queue.clear_active(record.run_id)
        return stale_run_ids

    async def tick(self) -> list[ExecutionResult]:
        """Execute one scheduler cycle."""

        results: list[ExecutionResult] = []
        mutation_result = await self.dispatch_next_mutation()
        if mutation_result is not None:
            results.append(mutation_result)
        self.cleanup_stale_runs()
        return results

    def _new_run_id(self) -> str:
        return f"run-{uuid4()}"


def main() -> None:
    """Run a single scheduler tick for manual smoke testing."""

    asyncio.run(ExecutionScheduler().tick())


if __name__ == "__main__":
    main()
