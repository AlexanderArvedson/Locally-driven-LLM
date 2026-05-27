"""Workflow execution boundary between the scheduler and LangGraph runtime."""

from __future__ import annotations

import asyncio

from src.graph.workflow import make_graph
from src.observability.context import RunContext
from src.runtime.models import (
    CancellationToken,
    ExecutionRequest,
    ExecutionResult,
    RunCancelledError,
    utc_now,
)
from src.runtime.state import (
    assert_clean_repository,
    restore_repository_state,
)


class WorkflowExecutor:
    """Execute workflow requests without exposing LangGraph internals upstream."""

    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        request: ExecutionRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> ExecutionResult:
        """Run the workflow request and return a structured execution result."""

        started_at = utc_now()
        state_snapshot = assert_clean_repository(request.repository_path)
        if state_snapshot.repository_revision != request.repository_revision:
            raise RuntimeError(
                "Repository revision mismatch: "
                f"expected {request.repository_revision}, got {state_snapshot.repository_revision}"
            )

        try:
            if cancellation_token is not None:
                cancellation_token.raise_if_cancelled()
            run_context = RunContext(run_id=request.run_id)
            graph = make_graph(run_context, cancellation_token=cancellation_token)
            workflow_output = await asyncio.wait_for(
                graph.ainvoke(request.payload),
                timeout=self.timeout_seconds,
            )
            if cancellation_token is not None:
                cancellation_token.raise_if_cancelled()
            completed_at = utc_now()
            return ExecutionResult(
                run_id=request.run_id,
                success=True,
                cancelled=False,
                started_at=started_at,
                completed_at=completed_at,
                artifacts={"workflow_output": workflow_output},
                metadata={
                    **request.metadata,
                    "repository_revision": request.repository_revision,
                    "workflow_mode": request.workflow_mode.value,
                    "workflow_capability": request.workflow_capability.value,
                },
            )
        except RunCancelledError as exc:
            restore_repository_state(request.repository_path)
            completed_at = utc_now()
            return ExecutionResult(
                run_id=request.run_id,
                success=False,
                cancelled=True,
                started_at=started_at,
                completed_at=completed_at,
                error=str(exc),
                artifacts={},
                metadata={
                    **request.metadata,
                    "repository_revision": request.repository_revision,
                    "workflow_mode": request.workflow_mode.value,
                    "workflow_capability": request.workflow_capability.value,
                },
            )
        except Exception as exc:
            restore_repository_state(request.repository_path)
            completed_at = utc_now()
            return ExecutionResult(
                run_id=request.run_id,
                success=False,
                cancelled=False,
                started_at=started_at,
                completed_at=completed_at,
                error=str(exc),
                artifacts={},
                metadata={
                    **request.metadata,
                    "repository_revision": request.repository_revision,
                    "workflow_mode": request.workflow_mode.value,
                    "workflow_capability": request.workflow_capability.value,
                },
            )
