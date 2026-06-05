from __future__ import annotations

import asyncio
import os

import uvicorn

from src.api.app import create_app
from src.api.tunnel import get_tunnel_url
from src.core.pipeline_config import load_pipeline_config
from src.scheduler.dispatcher import TaskDispatcher
from src.scheduler.loop import ExecutionLoop
from src.scheduler.queue import TaskQueue


async def _announce_tunnel() -> None:
    url = await get_tunnel_url()
    if url:
        print(f"Slack Request URL: {url}/slack/query", flush=True)
    else:
        print("ngrok tunnel not detected — verify NGROK_AUTHTOKEN and ngrok container", flush=True)


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

    asyncio.create_task(_announce_tunnel())

    try:
        await server.serve()
    finally:
        await loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
