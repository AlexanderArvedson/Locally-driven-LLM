from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .task_request import TaskRequest


TaskType = Literal["passive", "active"]


@dataclass(slots=True)
class Task:
    """Scheduler work unit wrapping a validated TaskRequest."""

    id: str
    type: TaskType
    request: TaskRequest
    created_at: float
