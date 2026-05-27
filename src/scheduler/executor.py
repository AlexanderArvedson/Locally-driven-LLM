from __future__ import annotations

from .task import Task


class WorkflowExecutor:
    def __init__(self) -> None:
        pass

    async def execute(self, task: Task):
        raise NotImplementedError
