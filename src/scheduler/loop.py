from __future__ import annotations

from .executor import WorkflowExecutor
from .queue import TaskQueue


class ExecutionLoop:
    def __init__(self, queue: TaskQueue, executor: WorkflowExecutor) -> None:
        self.queue = queue
        self.executor = executor

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def run(self) -> None:
        raise NotImplementedError
