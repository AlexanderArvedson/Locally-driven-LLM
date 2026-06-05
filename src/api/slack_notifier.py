"""Fire-and-forget Slack notification for pipeline completion events."""

import logging
import os

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

    if success and result is not None:
        text = (
            f"✅ Pipeline complete — {result.total_extracted} functions processed "
            f"in {result.duration_seconds:.0f}s"
        )
    else:
        text = f"❌ Pipeline failed — {error or 'unknown error'}"

    client = AsyncWebClient(token=token)
    try:
        await client.chat_postMessage(channel=channel, text=text)
    except Exception:
        logger.exception("Slack pipeline notification failed")
