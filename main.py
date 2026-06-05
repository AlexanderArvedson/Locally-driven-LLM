from __future__ import annotations

import asyncio

import uvicorn

from src.api.app import create_app
from src.api.slack_socket import start_socket_mode
from src.core.pipeline_config import load_pipeline_config
from src.scheduler.dispatcher import TaskDispatcher
from src.scheduler.loop import ExecutionLoop
from src.scheduler.queue import TaskQueue


async def main() -> None:
    config = load_pipeline_config()

    queue = TaskQueue()
    dispatcher = TaskDispatcher(pipeline_config=config)
    loop = ExecutionLoop(queue=queue, executor=dispatcher)
    await loop.start()

    socket_handler = await start_socket_mode(queue=queue, repo_name=config.repo_name)

    app = create_app()
    server_config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(server_config)

    try:
        await server.serve()
    finally:
        await loop.stop()
        if socket_handler is not None:
            await socket_handler.close_async()


if __name__ == "__main__":
    asyncio.run(main())
