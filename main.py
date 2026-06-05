from __future__ import annotations

import asyncio
import os

import uvicorn

from src.api.app import create_app
from src.core.pipeline_config import load_pipeline_config
from src.scheduler.dispatcher import TaskDispatcher
from src.scheduler.loop import ExecutionLoop
from src.scheduler.queue import TaskQueue


async def main() -> None:
    config = load_pipeline_config()
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")

    queue = TaskQueue()
    dispatcher = TaskDispatcher(pipeline_config=config)
    loop = ExecutionLoop(queue=queue, executor=dispatcher)
    await loop.start()

    app = create_app(queue=queue, signing_secret=signing_secret, repo_name=config.repo_name)
    server_config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(server_config)

    try:
        await server.serve()
    finally:
        await loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
