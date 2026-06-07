"""Fire-and-forget Slack notification for pipeline completion events."""

import datetime
import json
import os
from pathlib import Path

from loguru import logger
from slack_sdk.web.async_client import AsyncWebClient

from src.pipeline.contracts import PipelineResult


def _build_pipeline_blocks(result: PipelineResult) -> list:
    """Build a Slack Block Kit block list from a PipelineResult."""
    blocks: list = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "✅ Pipeline complete"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*New/modified:* {result.changed}\n"
                    f"*Unchanged:* {result.unchanged}\n"
                    f"*Deleted:* {result.newly_deleted}\n"
                    f"*Duration:* {result.duration_seconds:.0f}s"
                ),
            },
        },
    ]

    exclusions = []
    if result.loc_filtered:
        exclusions.append(f"{result.loc_filtered} below LOC threshold")

    if exclusions:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Excluded:* " + " · ".join(exclusions),
            },
        })

    return blocks


def _build_report_blocks(data: dict) -> list:
    """Build a Slack Block Kit block list from a parsed report.json dict."""
    stats = data.get("stats", {})
    emb = data.get("embedding", {}).get("code", {})
    sim = data.get("similarity_distribution", {})
    clusters = data.get("clusters", [])
    top_pairs = data.get("top_pairs", [])
    flags_raw = data.get("flags", {})
    delta = data.get("delta")

    blocks: list = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"\U0001f4ca {data.get('repo', '?')} — {data.get('timestamp', '?')}"},
    })

    # Graph overview — one value per line
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Graph*\n"
                f"Functions: {stats.get('total_functions', '?')}\n"
                f"Edges: {stats.get('edges', '?')}   Density: {stats.get('density', 0):.2f}\n"
                f"Intra: {stats.get('intra_edges', '?')}   Inter: {stats.get('inter_edges', '?')}   Isolated: {stats.get('isolated_functions', 0)}"
            ),
        },
    })

    # Embedding health
    failed = emb.get("failed_total", emb.get("context_overflow", 0) + emb.get("error", 0))
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Embedding*\n"
                f"OK: {emb.get('ok', '?')}\n"
                f"Failed: {failed}   ({emb.get('context_overflow', 0)} overflow · {emb.get('error', 0)} error)"
            ),
        },
    })

    # Similarity bands
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Similarity*\n"
                f">0.95: {sim.get('gt95', 0)}\n"
                f"0.90–0.95: {sim.get('b90_95', 0)}\n"
                f"0.80–0.90: {sim.get('b80_90', 0)}"
            ),
        },
    })

    # Delta since previous run (omit if no previous report)
    if delta and delta.get("previous_timestamp"):
        def _fmt(n: int) -> str:
            return f"+{n}" if n >= 0 else str(n)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Δ vs {delta['previous_timestamp']}*\n"
                    f"Functions: {_fmt(delta.get('functions', 0))}\n"
                    f"Edges: {_fmt(delta.get('edges', 0))}\n"
                    f"Clusters: {_fmt(delta.get('clusters', 0))}"
                ),
            },
        })

    # Duplication clusters (omit if empty)
    if clusters:
        largest = clusters[0]
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Duplication clusters: {len(clusters)}*\n"
                    f"Largest: {largest.get('representative', '?')}\n"
                    f"{largest.get('size', '?')} functions, avg score {largest.get('avg_score', 0):.3f}"
                ),
            },
        })

    # Raised flags — one flag per line (omit block if none)
    raised = []
    for flag in ("HIGH_DUPLICATION_CLUSTER", "CROSS_FILE_DUPLICATION", "ARCHITECTURE_COUPLING"):
        val = flags_raw.get(flag)
        if val:
            raised.append(flag)
    test_poll = flags_raw.get("TEST_POLLUTION")
    if isinstance(test_poll, int) and test_poll > 0:
        raised.append("TEST_POLLUTION")
    god_files = flags_raw.get("GOD_FILE")
    if god_files:
        raised.append(f"GOD_FILE ({len(god_files)} files)")
    low_coh = flags_raw.get("LOW_COHESION")
    if low_coh:
        raised.append(f"LOW_COHESION ({len(low_coh)} files)")

    if raised:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Flags*\n\U0001f6a8 " + "\n\U0001f6a8 ".join(raised),
            },
        })

    # Top pair (omit if empty)
    if top_pairs:
        pair = top_pairs[0]
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Top pair*\n"
                    f"{pair.get('a_name', '?')} ↔ {pair.get('b_name', '?')}\n"
                    f"Score: {pair.get('score', 0):.4f}"
                ),
            },
        })

    return blocks


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

    client = AsyncWebClient(token=token)
    try:
        if not success or result is None:
            await client.chat_postMessage(
                channel=channel,
                text=f"❌ Pipeline failed — {error or 'unknown error'}",
            )
        else:
            blocks = _build_pipeline_blocks(result)
            await client.chat_postMessage(
                channel=channel,
                text=f"✅ Pipeline complete — {result.changed} new/modified in {result.duration_seconds:.0f}s",
                blocks=blocks,
            )
    except Exception:
        logger.exception("Slack pipeline notification failed")


async def notify_report_result(
    success: bool,
    started_at: datetime.datetime,
    report_path: Path | None,
    error: str | None,
) -> None:
    """Post a Block Kit report summary and upload the .md file on success.

    Reads the adjacent report.json to build a structured Block Kit message.
    Falls back to a plain text message if report.json is missing or malformed.
    Silently skips when SLACK_BOT_TOKEN or SLACK_NOTIFY_CHANNEL is unset.
    Swallows Slack API errors so a Slack outage never breaks the pipeline.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("SLACK_NOTIFY_CHANNEL", "")
    if not token or not channel:
        return

    time_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
    client = AsyncWebClient(token=token)
    try:
        if not success:
            await client.chat_postMessage(
                channel=channel,
                text=f"❌ Report started at {time_str} — failed: {error or 'unknown error'}",
            )
            return

        blocks = None
        if report_path is not None:
            json_path = report_path.with_suffix(".json")
            if json_path.exists():
                try:
                    blocks = _build_report_blocks(json.loads(json_path.read_text()))
                except Exception:
                    logger.warning("Could not parse report.json for Block Kit; falling back to plain text")

        if blocks:
            await client.chat_postMessage(
                channel=channel,
                text=f"✅ Report — {time_str}",
                blocks=blocks,
            )
        else:
            await client.chat_postMessage(
                channel=channel,
                text=f"✅ Report started at {time_str} — finished",
            )

        if report_path is not None and report_path.exists():
            await client.files_upload_v2(
                channel=channel,
                file=str(report_path),
                filename=report_path.name,
                title=f"Report — {time_str}",
            )
    except Exception:
        logger.exception("Slack report notification failed")


async def notify_scheduled_run(repo: str, cron_expr: str) -> None:
    """Post a notice to Slack that a cron-triggered pipeline run has been queued.

    Silently skips when SLACK_BOT_TOKEN or SLACK_NOTIFY_CHANNEL is unset.
    Swallows Slack API errors so a Slack outage never blocks scheduling.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("SLACK_NOTIFY_CHANNEL", "")
    if not token or not channel:
        return

    client = AsyncWebClient(token=token)
    try:
        await client.chat_postMessage(
            channel=channel,
            text=f"Scheduled pipeline run started or queued for repo: {repo} ",
        )
    except Exception:
        logger.exception("Slack scheduled-run notification failed")
