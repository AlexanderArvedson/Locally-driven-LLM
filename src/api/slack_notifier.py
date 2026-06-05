"""Fire-and-forget Slack notification for pipeline completion events."""

import datetime
import logging
import os
from pathlib import Path

from slack_sdk.web.async_client import AsyncWebClient

from src.pipeline.contracts import PipelineResult

logger = logging.getLogger(__name__)


async def notify_pipeline_result(
    success: bool,
    result: PipelineResult | None,
    error: str | None,
) -> None:
    """Post a pipeline completion or failure notice to the configured Slack channel.

    Silently skips when SLACK_BOT_TOKEN or SLACK_NOTIFY_CHANNEL is unset.
    Swallows Slack API errors so a Slack outage never breaks the pipeline.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("SLACK_NOTIFY_CHANNEL", "")
    if not token or not channel:
        return

    if not success or result is None:
        text = f"❌ Pipeline failed — {error or 'unknown error'}"
    else:
        text = (
            f"Pipeline run complete — {result.total_extracted} functions processed "
            f"in {result.duration_seconds:.0f}s"
        )

    client = AsyncWebClient(token=token)
    try:
        await client.chat_postMessage(channel=channel, text=text)
    except Exception:
        logger.exception("Slack pipeline notification failed")


async def notify_report_result(
    success: bool,
    started_at: datetime.datetime,
    report_path: Path | None,
    error: str | None,
) -> None:
    """Post a report completion notice and upload the .md file on success.

    Silently skips when SLACK_BOT_TOKEN or SLACK_NOTIFY_CHANNEL is unset.
    Swallows Slack API errors so a Slack outage never breaks the pipeline.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("SLACK_NOTIFY_CHANNEL", "")
    if not token or not channel:
        return

    time_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
    if success:
        text = f"✅ Report started at {time_str} — finished"
    else:
        text = f"❌ Report started at {time_str} — failed: {error or 'unknown error'}"

    client = AsyncWebClient(token=token)
    try:
        await client.chat_postMessage(channel=channel, text=text)
        if success and report_path is not None and report_path.exists():
            await client.files_upload_v2(
                channel=channel,
                file=str(report_path),
                filename="report.md",
                title=f"Report — {time_str}",
            )
    except Exception:
        logger.exception("Slack report notification failed")
