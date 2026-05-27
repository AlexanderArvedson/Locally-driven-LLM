from __future__ import annotations

import asyncio
import signal

from src.scheduler.executor import WorkflowExecutor
from src.scheduler.loop import ExecutionLoop
from src.scheduler.queue import TaskQueue


async def main() -> None:
    queue = TaskQueue()
    executor = WorkflowExecutor()
    loop = ExecutionLoop(queue=queue, executor=executor)

    await loop.start()

    stop_event = asyncio.Event()
    event_loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            event_loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    finally:
        await loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
