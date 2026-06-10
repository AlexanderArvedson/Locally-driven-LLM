"""Pipeline progress notifier for Slack.

Posts stage lifecycle events and periodic progress updates to a Slack thread.
One message is posted to the channel when the pipeline starts; all subsequent
updates are thread replies. The original message is updated via chat_update
when the pipeline completes or fails.

All methods are fire-and-forget: Slack errors are swallowed so a Slack outage
never affects pipeline execution.
"""

from __future__ import annotations

import math
import os
import time

from loguru import logger
from slack_sdk.web.async_client import AsyncWebClient

from src.git.branch_manager import SyncResult
from src.pipeline.contracts import PipelineResult, SlackPipelineConfig


def _fmt_duration(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"


def _fmt_eta(remaining_seconds: float) -> str:
    """Format remaining seconds as 'Xh Ym remaining' or similar."""
    return f"{_fmt_duration(remaining_seconds)} remaining"


class PipelineProgressNotifier:
    """Posts pipeline lifecycle and progress updates to a Slack thread.

    Thread strategy: pipeline_start() posts to the channel and stores thread_ts.
    All subsequent calls post as replies to that thread. pipeline_complete() and
    pipeline_failed() also update the original channel message via chat_update
    so the channel shows the final outcome without scrolling into the thread.
    """

    def __init__(self, config: SlackPipelineConfig) -> None:
        self._enabled = config.enabled
        self._debug = config.debug_messages
        self._interval = config.progress_update_interval
        self._thread_ts: str | None = None
        self._message_ts: str | None = None
        self._channel: str = ""
        self._client: AsyncWebClient | None = None

    def _get_client(self) -> AsyncWebClient | None:
        """Return a configured client, or None if Slack is not set up."""
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        channel = os.environ.get("SLACK_NOTIFY_CHANNEL", "")
        if not token or not channel:
            return None
        self._channel = channel
        if self._client is None:
            self._client = AsyncWebClient(token=token)
        return self._client

    async def _reply(self, text: str) -> None:
        """Post text as a thread reply (or to channel if no thread yet)."""
        client = self._get_client()
        if client is None:
            return
        try:
            kwargs: dict = {"channel": self._channel, "text": text}
            if self._thread_ts is not None:
                kwargs["thread_ts"] = self._thread_ts
            await client.chat_postMessage(**kwargs)
        except Exception:
            logger.exception("Slack reply failed")

    async def pipeline_start(self, repo: str) -> None:
        """Post the initial channel message and store thread_ts for replies."""
        if not self._enabled:
            return
        client = self._get_client()
        if client is None:
            return
        try:
            resp = await client.chat_postMessage(
                channel=self._channel,
                text=f"Pipeline starting for *{repo}*…",
            )
            self._message_ts = resp["ts"]
            self._thread_ts = resp["ts"]
        except Exception:
            logger.exception("Slack pipeline_start notification failed")

    async def pipeline_complete(self, result: PipelineResult) -> None:
        """Update the original channel message and post a thread summary."""
        if not self._enabled:
            return
        client = self._get_client()
        if client is None:
            return

        summary = (
            f"Pipeline completed successfully.\n\n"
            f"Functions extracted: {result.total_extracted:,}\n"
            f"Embeddings generated: {result.changed:,}\n"
            f"Relationships created: {result.edges_written:,}\n\n"
            f"Total runtime: {_fmt_duration(result.duration_seconds)}"
        )
        try:
            if self._message_ts:
                await client.chat_update(
                    channel=self._channel,
                    ts=self._message_ts,
                    text=f"✅ Pipeline complete — {result.changed:,} changed, {_fmt_duration(result.duration_seconds)}",
                )
            await self._reply(f"✅ {summary}")
        except Exception:
            logger.exception("Slack pipeline_complete notification failed")

    async def pipeline_failed(self, error: str) -> None:
        """Update the original channel message and post a thread failure notice."""
        if not self._enabled:
            return
        client = self._get_client()
        if client is None:
            return
        try:
            if self._message_ts:
                await client.chat_update(
                    channel=self._channel,
                    ts=self._message_ts,
                    text=f"❌ Pipeline failed",
                )
            await self._reply(f"❌ Pipeline failed.\n\nReason:\n{error}")
        except Exception:
            logger.exception("Slack pipeline_failed notification failed")

    async def sync_start(self) -> None:
        """Notify that repository synchronisation has started."""
        if not self._enabled or not self._debug:
            return
        await self._reply("Repository lookup started…")

    async def sync_complete(self, result: SyncResult) -> None:
        """Post a sync summary and, when debug_messages is on, operation detail."""
        if not self._enabled:
            return

        if result.operation == "clone":
            detail = "Repository not present locally.\nStarting repository clone…"
            if result.success:
                outcome = "Repository clone completed successfully."
            else:
                outcome = f"Repository clone failed.\n\nReason:\n{result.error or 'unknown'}"
        elif result.operation == "pull":
            detail = "Local repository found.\nPulling latest changes…"
            if not result.success:
                outcome = f"Pull failed.\n\nReason:\n{result.error or 'unknown'}"
            elif result.already_up_to_date:
                outcome = "Already up to date."
            else:
                outcome = "Repository successfully updated."
        else:  # skipped
            detail = "Local repository found (uncommitted changes — skipping pull)."
            outcome = None

        if self._debug:
            await self._reply(detail)

        if outcome:
            await self._reply(outcome)

        commit_str = result.commit_hash or "unknown"
        status_str = "Success" if result.success else "Failed"
        summary = (
            f"Repository synchronisation completed.\n\n"
            f"Operation: {result.operation.capitalize()}\n"
            f"Branch: {result.branch}\n"
            f"Commit: {commit_str}\n"
            f"Status: {status_str}"
        )
        await self._reply(summary)

    async def extraction_complete(self, files: int, functions: int, duration: float) -> None:
        """Post extraction stage completion summary."""
        if not self._enabled:
            return
        msg = (
            f"Function extraction completed.\n\n"
            f"Files processed: {files:,}\n"
            f"Functions extracted: {functions:,}\n"
            f"Duration: {_fmt_duration(duration)}"
        )
        await self._reply(msg)

    async def embedding_start(self, count: int, stage: str) -> None:
        """Notify that an embedding stage has started."""
        if not self._enabled or not self._debug:
            return
        label = "Code embedding" if stage == "code" else "Description embedding"
        await self._reply(f"{label} started for {count:,} functions…")

    async def embedding_complete(
        self, generated: int, failures: int, duration: float, stage: str
    ) -> None:
        """Post embedding stage completion summary."""
        if not self._enabled:
            return
        label = "Code embeddings" if stage == "code" else "Description embeddings"
        msg = (
            f"{label} completed.\n\n"
            f"Generated embeddings: {generated:,}\n"
            f"Failures: {failures:,}\n"
            f"Duration: {_fmt_duration(duration)}"
        )
        await self._reply(msg)

    async def description_start(self, count: int) -> None:
        """Notify that description generation has started."""
        if not self._enabled or not self._debug:
            return
        await self._reply(f"Description generation started for {count:,} functions…")

    async def description_complete(
        self, generated: int, skipped: int, duration: float
    ) -> None:
        """Post description generation completion summary."""
        if not self._enabled:
            return
        msg = (
            f"Description generation completed.\n\n"
            f"Generated descriptions: {generated:,}\n"
            f"Skipped: {skipped:,}\n"
            f"Duration: {_fmt_duration(duration)}"
        )
        await self._reply(msg)

    async def similarity_start(self, count: int) -> None:
        """Notify that similarity analysis has started."""
        if not self._enabled or not self._debug:
            return
        await self._reply(f"Similarity analysis started for {count:,} functions…")

    async def similarity_complete(self, relationships: int, duration: float) -> None:
        """Post similarity analysis completion summary."""
        if not self._enabled:
            return
        msg = (
            f"Similarity analysis completed.\n\n"
            f"Relationships created: {relationships:,}\n"
            f"Duration: {_fmt_duration(duration)}"
        )
        await self._reply(msg)

    async def progress(
        self, stage: str, processed: int, total: int, stage_start: float
    ) -> None:
        """Post a progress update, throttled to once per configured interval.

        Called once per processed item; only sends to Slack when
        processed is a multiple of progress_update_interval.
        """
        if not self._enabled:
            return
        if self._interval <= 0 or processed % self._interval != 0:
            return

        elapsed = time.monotonic() - stage_start
        pct = (processed / total * 100) if total > 0 else 0.0
        rate = processed / elapsed if elapsed > 0 else 0.0

        remaining = total - processed
        eta_str = _fmt_eta(remaining / rate) if rate > 0 else "unknown"

        msg = (
            f"{stage} progress\n\n"
            f"Processed: {processed:,} / {total:,}\n"
            f"Progress: {pct:.1f}%\n"
            f"Rate: {rate:.0f} items/sec\n"
            f"Elapsed: {_fmt_duration(elapsed)}\n"
            f"ETA: {eta_str}"
        )
        await self._reply(msg)
