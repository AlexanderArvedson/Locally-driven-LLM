"""Execution contracts shared across the scheduler/runtime boundary.

These models stay framework-agnostic so orchestration code can coordinate
workflow execution without depending on LangGraph internals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class RunStatus(str, Enum):
    """Lifecycle states for a persisted execution run."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowMode(str, Enum):
    """High-level workflow intent."""

    PASSIVE = "passive"
    ACTIVE = "active"


class WorkflowCapability(str, Enum):
    """Mutability classification for execution coordination."""

    READ_ONLY = "read_only"
    MUTATING = "mutating"


class RunCancelledError(RuntimeError):
    """Raised when cooperative cancellation is observed for a run."""


@dataclass(slots=True, frozen=True)
class CancellationToken:
    """Cooperative cancellation signal shared across scheduler and executor."""

    run_id: str
    is_cancelled: Callable[[], bool]

    def raise_if_cancelled(self) -> None:
        """Raise when cancellation has been requested for this run."""

        if self.is_cancelled():
            raise RunCancelledError(f"Run cancelled: {self.run_id}")


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime | None) -> str | None:
    """Serialize a datetime as an ISO-8601 UTC string.

    Accept `None` and return `None` to simplify callers that may
    optionally pass timestamps.
    """

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@dataclass(slots=True, frozen=True)
class ExecutionRequest:
    """Scheduler-issued request to execute a workflow."""

    run_id: str
    workflow_mode: WorkflowMode
    workflow_capability: WorkflowCapability
    trigger: str
    repository_path: Path
    repository_revision: str
    created_at: datetime
    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the request."""

        data = asdict(self)
        data["workflow_mode"] = self.workflow_mode.value
        data["workflow_capability"] = self.workflow_capability.value
        data["repository_path"] = str(self.repository_path)
        data["created_at"] = isoformat_utc(self.created_at)
        return data


@dataclass(slots=True, frozen=True)
class ExecutionResult:
    """Structured result returned by the workflow executor."""

    run_id: str
    success: bool
    started_at: datetime
    completed_at: datetime
    cancelled: bool = False
    error: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the result."""

        data = asdict(self)
        data["started_at"] = isoformat_utc(self.started_at)
        data["completed_at"] = isoformat_utc(self.completed_at)
        return data
