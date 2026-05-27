"""In-memory FIFO queue for mutation-oriented workflow requests."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from src.runtime.models import ExecutionRequest, WorkflowCapability


@dataclass(slots=True)
class MutationQueue:
    """Deterministic queue for active mutation workflows."""

    _items: Deque[ExecutionRequest] = field(default_factory=deque)
    _active_run_id: str | None = None

    def enqueue(self, request: ExecutionRequest) -> None:
        """Add a mutating workflow request to the queue."""

        if request.workflow_capability != WorkflowCapability.MUTATING:
            raise ValueError("MutationQueue only accepts mutating workflow requests")
        self._items.append(request)

    def remove(self, run_id: str) -> bool:
        """Remove a queued request by run id.

        Returns True when a queued request was removed. Running requests are
        not removed because they are no longer in the FIFO queue.
        """

        if self._active_run_id == run_id:
            return False

        removed = False
        retained: Deque[ExecutionRequest] = deque()
        while self._items:
            request = self._items.popleft()
            if request.run_id == run_id:
                removed = True
                continue
            retained.append(request)
        self._items = retained
        return removed

    def dequeue(self) -> ExecutionRequest | None:
        """Remove and return the next request in FIFO order."""

        if self._active_run_id is not None:
            return None
        if not self._items:
            return None
        return self._items.popleft()

    def mark_active(self, run_id: str) -> None:
        """Mark a queued mutation workflow as actively executing."""

        if self._active_run_id is not None and self._active_run_id != run_id:
            raise RuntimeError(f"Mutation workflow already active: {self._active_run_id}")
        self._active_run_id = run_id

    def clear_active(self, run_id: str) -> None:
        """Clear the active mutation marker when execution completes."""

        if self._active_run_id == run_id:
            self._active_run_id = None

    @property
    def active_run_id(self) -> str | None:
        return self._active_run_id

    def has_active_mutation(self) -> bool:
        return self._active_run_id is not None

    def __len__(self) -> int:
        return len(self._items)
