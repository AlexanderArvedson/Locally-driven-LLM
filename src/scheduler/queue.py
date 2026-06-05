from __future__ import annotations

import asyncio

from .slack_task import SlackTask


class TaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[SlackTask] = asyncio.Queue()

    async def enqueue(self, task: SlackTask) -> None:
        await self._queue.put(task)

    async def dequeue(self) -> SlackTask:
        return await self._queue.get()
