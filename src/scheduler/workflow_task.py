"""Legacy task type for the LangGraph workflow system.

WorkflowTask wraps a TaskRequest and was the scheduler's work unit when the
execution backend was WorkflowExecutor + LangGraph. It is not currently wired
into the active scheduler (TaskDispatcher / ExecutionLoop). Re-integration
would require updating WorkflowExecutor.execute() and either re-exporting
WorkflowTask from this module or routing it through the Task union in task.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .task_request import TaskRequest


TaskType = Literal["passive", "active"]


@dataclass(slots=True)
class WorkflowTask:
    """Scheduler work unit wrapping a validated TaskRequest."""

    id: str
    type: TaskType
    request: TaskRequest
    created_at: float
