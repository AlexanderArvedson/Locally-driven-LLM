from __future__ import annotations

import asyncio

from .dispatcher import TaskDispatcher
from .queue import TaskQueue
from .slack_task import SlackTask



class ExecutionLoop:
    """Background execution loop that consumes tasks from a `TaskQueue`.

    Responsibilities:
    - Start and stop the background consumer task.
    - Dispatch passive tasks as background work and run active tasks
      serially while holding a mutation lock.
    - Track background tasks to ensure orderly shutdown.
    """

    def __init__(self, queue: TaskQueue, executor: TaskDispatcher) -> None:
        self.queue = queue
        self.executor = executor
        self._mutation_lock = asyncio.Lock()
        self._started = False
        self._consumer_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task[object]] = set()

    async def start(self) -> None:
        if self._started:
            return

        self._started = True
        self._consumer_task = asyncio.create_task(self._consume())

    async def submit_task(self, task: SlackTask) -> None:
        if not self._started:
            await self.start()

        await self.queue.enqueue(task)

    async def stop(self) -> None:
        if not self._started:
            return

        self._started = False

        if self._consumer_task is not None:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    async def run(self) -> None:
        await self.start()
        try:
            while self._started:
                await asyncio.sleep(0)
        finally:
            await self.stop()

    async def _consume(self) -> None:
        while True:
            task = await self.queue.dequeue()
            if task.type == "passive":
                background_task = asyncio.create_task(self.executor.execute(task))
                self._background_tasks.add(background_task)
                background_task.add_done_callback(self._background_tasks.discard)
                continue

            async with self._mutation_lock:
                await self.executor.execute(task)