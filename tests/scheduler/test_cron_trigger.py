"""Unit tests for CronTrigger.

asyncio.sleep is mocked to return immediately so tests run without real delays.
notify_scheduled_run is mocked so tests run without a live Slack workspace.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.scheduler.cron_trigger import CronTrigger
from src.scheduler.queue import TaskQueue
from src.scheduler.task import PipelineTask


EVERY_MINUTE = "* * * * *"
DAILY_MIDNIGHT = "0 0 * * *"


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_invalid_cron_expression_raises():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        CronTrigger(cron_expr="not-a-cron", repo="myrepo", queue=TaskQueue())


def test_valid_cron_expression_does_not_raise():
    CronTrigger(cron_expr=EVERY_MINUTE, repo="myrepo", queue=TaskQueue())


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_before_start_is_noop():
    trigger = CronTrigger(cron_expr=EVERY_MINUTE, repo="myrepo", queue=TaskQueue())
    await trigger.stop()  # must not raise


@pytest.mark.asyncio
async def test_double_start_is_idempotent():
    """Calling start() twice must not spawn a second background task."""
    queue = TaskQueue()
    trigger = CronTrigger(cron_expr=EVERY_MINUTE, repo="myrepo", queue=queue)

    block = asyncio.Event()  # never set — used to park the loop after first fire
    fired = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        if fired.is_set():
            await block.wait()  # parks here until CancelledError from stop()
            return
        fired.set()

    with (
        patch("src.scheduler.cron_trigger.asyncio.sleep", side_effect=fake_sleep),
        patch("src.api.slack_notifier.notify_scheduled_run", new=AsyncMock()),
    ):
        await trigger.start()
        task_after_first_start = trigger._task

        await trigger.start()  # second call — must be idempotent
        assert trigger._task is task_after_first_start

        await asyncio.wait_for(fired.wait(), timeout=2)
        await trigger.stop()


# ---------------------------------------------------------------------------
# Task enqueue behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_task_enqueued_on_fire():
    queue = TaskQueue()
    trigger = CronTrigger(cron_expr=EVERY_MINUTE, repo="myrepo", queue=queue)

    block = asyncio.Event()
    fired = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        if fired.is_set():
            await block.wait()
            return
        fired.set()

    with (
        patch("src.scheduler.cron_trigger.asyncio.sleep", side_effect=fake_sleep),
        patch("src.api.slack_notifier.notify_scheduled_run", new=AsyncMock()),
    ):
        await trigger.start()
        await asyncio.wait_for(fired.wait(), timeout=2)
        await trigger.stop()

    task = queue._queue.get_nowait()
    assert isinstance(task, PipelineTask)
    assert task.repo == "myrepo"


@pytest.mark.asyncio
async def test_correct_repo_name_in_task():
    queue = TaskQueue()
    trigger = CronTrigger(cron_expr=EVERY_MINUTE, repo="special-repo", queue=queue)

    block = asyncio.Event()
    fired = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        if fired.is_set():
            await block.wait()
            return
        fired.set()

    with (
        patch("src.scheduler.cron_trigger.asyncio.sleep", side_effect=fake_sleep),
        patch("src.api.slack_notifier.notify_scheduled_run", new=AsyncMock()),
    ):
        await trigger.start()
        await asyncio.wait_for(fired.wait(), timeout=2)
        await trigger.stop()

    task = queue._queue.get_nowait()
    assert task.repo == "special-repo"


@pytest.mark.asyncio
async def test_multiple_fires_enqueue_multiple_tasks():
    queue = TaskQueue()
    trigger = CronTrigger(cron_expr=EVERY_MINUTE, repo="myrepo", queue=queue)

    fires = 0
    block = asyncio.Event()
    done = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        nonlocal fires
        fires += 1
        # sleep N is called before enqueue N, so wait for sleep 4
        # to confirm enqueues 1-3 are all done
        if fires >= 4:
            done.set()
            await block.wait()  # park here until stop()
            return

    with (
        patch("src.scheduler.cron_trigger.asyncio.sleep", side_effect=fake_sleep),
        patch("src.api.slack_notifier.notify_scheduled_run", new=AsyncMock()),
    ):
        await trigger.start()
        await asyncio.wait_for(done.wait(), timeout=2)
        await trigger.stop()

    tasks = []
    while not queue._queue.empty():
        tasks.append(queue._queue.get_nowait())

    assert len(tasks) == 3
    assert all(isinstance(t, PipelineTask) for t in tasks)


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slack_notify_called_on_fire():
    queue = TaskQueue()
    trigger = CronTrigger(cron_expr=EVERY_MINUTE, repo="myrepo", queue=queue)

    block = asyncio.Event()
    fired = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        if fired.is_set():
            await block.wait()
            return
        fired.set()

    mock_notify = AsyncMock()
    with (
        patch("src.scheduler.cron_trigger.asyncio.sleep", side_effect=fake_sleep),
        patch("src.api.slack_notifier.notify_scheduled_run", mock_notify),
    ):
        await trigger.start()
        await asyncio.wait_for(fired.wait(), timeout=2)
        await trigger.stop()

    mock_notify.assert_called_once_with("myrepo", EVERY_MINUTE)


@pytest.mark.asyncio
async def test_slack_notify_called_with_correct_cron_expr():
    queue = TaskQueue()
    trigger = CronTrigger(cron_expr=DAILY_MIDNIGHT, repo="repo-x", queue=queue)

    block = asyncio.Event()
    fired = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        if fired.is_set():
            await block.wait()
            return
        fired.set()

    mock_notify = AsyncMock()
    with (
        patch("src.scheduler.cron_trigger.asyncio.sleep", side_effect=fake_sleep),
        patch("src.api.slack_notifier.notify_scheduled_run", mock_notify),
    ):
        await trigger.start()
        await asyncio.wait_for(fired.wait(), timeout=2)
        await trigger.stop()

    _, call_cron = mock_notify.call_args.args
    assert call_cron == DAILY_MIDNIGHT
