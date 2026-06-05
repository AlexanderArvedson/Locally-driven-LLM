from __future__ import annotations

import asyncio

from .task import Task


class TaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Task] = asyncio.Queue()

    async def enqueue(self, task: Task) -> None:
        await self._queue.put(task)

    async def dequeue(self) -> Task:
        return await self._queue.get()
