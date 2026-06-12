"""Slack Socket Mode integration.

Opens a persistent WebSocket connection to Slack so slash commands are
delivered without requiring a public URL or tunnel.
"""

from __future__ import annotations

import argparse
import os
import shlex
import uuid

from loguru import logger
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from src.scheduler.queue import TaskQueue
from src.scheduler.task import PipelineTask, QueryTask, ReportTask

_PIPELINE_USAGE = (
    "Usage: `/pipeline [--no-descriptions] [--dry-run] [--no-report] [--path PATH]`"
)


def _parse_pipeline_args(text: str) -> argparse.Namespace | str:
    """Parse /pipeline argument string. Returns Namespace on success, error string on failure."""
    parser = argparse.ArgumentParser(prog="/pipeline", add_help=False, exit_on_error=False)
    parser.add_argument("--no-descriptions", action="store_true", dest="no_descriptions")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--no-report", action="store_true", dest="no_report")
    parser.add_argument("--path", default=None)
    try:
        return parser.parse_args(shlex.split(text) if text else [])
    except (argparse.ArgumentError, ValueError) as exc:
        return str(exc)


async def start_socket_mode(queue: TaskQueue, repo_name: str) -> AsyncSocketModeHandler | None:
    """Connect to Slack via Socket Mode and register slash command handlers.

    Returns None and logs a warning if the required tokens are not set,
    so the rest of the app still starts cleanly.
    """
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    app_token = os.environ.get("SLACK_APP_TOKEN", "")

    if not bot_token or not app_token:
        logger.warning(
            "SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set — Socket Mode disabled, slash commands will not work"
        )
        return None

    app = AsyncApp(token=bot_token)

    @app.command("/query")
    async def handle_query(ack, body, respond) -> None:
        await ack()
        query_text = body.get("text", "").strip()
        if not query_text:
            await respond(
                "Usage: `/query <description>`\n"
                "Tip: describe the *behaviour*, not the location — "
                "e.g. `/query AES encrypt decrypt value` rather than `/query where is crypto handled?`"
            )
            return
        await queue.enqueue(
            QueryTask(
                id=str(uuid.uuid4()),
                query_text=query_text,
                response_url=body["response_url"],
                repo=repo_name,
            )
        )
        await respond({"response_type": "ephemeral", "text": f"Searching for: _{query_text}_…"})

    @app.command("/pipeline")
    async def handle_pipeline(ack, body, respond) -> None:
        await ack()
        args = _parse_pipeline_args(body.get("text", "").strip())
        if isinstance(args, str):
            await respond({"response_type": "ephemeral", "text": f"Invalid arguments: {args}\n{_PIPELINE_USAGE}"})
            return
        await queue.enqueue(
            PipelineTask(
                id=str(uuid.uuid4()),
                repo=repo_name,
                no_descriptions=args.no_descriptions,
                dry_run=args.dry_run,
                no_report=args.no_report,
                path=args.path,
            )
        )
        await respond({"response_type": "ephemeral", "text": "Pipeline run queued."})

    @app.command("/report")
    async def handle_report(ack, respond) -> None:
        await ack()
        await queue.enqueue(
            ReportTask(
                id=str(uuid.uuid4()),
                repo=repo_name,
            )
        )
        await respond({"response_type": "ephemeral", "text": "Report generation queued."})

    handler = AsyncSocketModeHandler(app, app_token)
    await handler.start_async()
    logger.info("Slack Socket Mode connected — slash commands are live")
    return handler
