"""Cron-based pipeline trigger.

Reads a cron expression and enqueues a PipelineTask for the configured
repository at each scheduled fire time. A Slack notice is posted before
the task is enqueued so operators know the run is coming.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from croniter import croniter
from loguru import logger

from .queue import TaskQueue
from .task import PipelineTask


class CronTrigger:
    """Fires a PipelineTask on a cron schedule.

    Args:
        cron_expr: Standard 5-part cron expression (e.g. ``"0 0 * * *"``).
        repo: Repository name passed to the enqueued PipelineTask.
        queue: Queue into which PipelineTask instances are enqueued.

    Raises:
        ValueError: If ``cron_expr`` is not a valid cron expression.
    """

    def __init__(self, cron_expr: str, repo: str, queue: TaskQueue) -> None:
        if not croniter.is_valid(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr!r}")
        self._cron_expr = cron_expr
        self._repo = repo
        self._queue = queue
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background scheduling loop. Idempotent."""
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            logger.info("[cron] scheduler started — repo={} expr={!r}", self._repo, self._cron_expr)

    async def stop(self) -> None:
        """Cancel the scheduling loop and wait for it to exit. Idempotent."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("[cron] scheduler stopped")

    async def _run(self) -> None:
        while True:
            now = time.time()
            next_fire = croniter(self._cron_expr, now).get_next(float)
            delay = next_fire - time.time()
            if delay > 0:
                logger.debug("[cron] next fire in {:.0f}s", delay)
                await asyncio.sleep(delay)

            logger.info("[cron] firing scheduled pipeline run — repo={}", self._repo)

            from src.api.slack_notifier import notify_scheduled_run
            await notify_scheduled_run(self._repo, self._cron_expr)

            await self._queue.enqueue(
                PipelineTask(id=str(uuid.uuid4()), repo=self._repo)
            )
