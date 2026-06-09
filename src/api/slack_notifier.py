"""Fire-and-forget Slack notification for pipeline completion events."""

import datetime
import json
import os
from pathlib import Path

from loguru import logger
from slack_sdk.web.async_client import AsyncWebClient

from src.pipeline.contracts import PipelineResult, ReporterConfig


def _build_pipeline_blocks(result: PipelineResult) -> list:
    """Build a Slack Block Kit block list from a PipelineResult."""
    blocks: list = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "✅ Pipeline complete"},
        },
        {"type": "divider"},
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


_FLAG_LABELS = {
    "HIGH_DUPLICATION_CLUSTER": "High duplication — large groups of near-identical functions",
    "CROSS_FILE_DUPLICATION": "Cross-file duplication — same logic copied across multiple files",
    "ARCHITECTURE_COUPLING": "High coupling — some files heavily depended on across the codebase",
}


def _build_report_blocks(data: dict, reporter_cfg: ReporterConfig | None = None) -> list:
    """Build a Slack Block Kit block list from a parsed report.json dict."""
    if reporter_cfg is None:
        reporter_cfg = ReporterConfig()
    top_n = reporter_cfg.slack_top_n_report

    stats = data.get("stats", {})
    emb = data.get("embedding", {}).get("code", {})
    desc = data.get("embedding", {}).get("description", {})
    sim = data.get("similarity_distribution", {})
    clusters = data.get("clusters", [])
    top_pairs = data.get("top_pairs", [])
    flags_raw = data.get("flags", {})
    delta = data.get("delta")
    summary = data.get("summary", "")

    blocks: list = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"\U0001f4ca {data.get('repo', '?')} — {data.get('timestamp', '?')}"},
    })

    # Executive summary (omit if absent)
    if summary:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary}"},
        })

    # Graph overview — one value per line
    loc_filtered = stats.get("loc_filtered")
    graph_text = (
        f"*Graph*\n"
        f"Functions: {stats.get('total_functions', '?')}\n"
        f"Edges: {stats.get('edges', '?')}\n"
        f"Density: {stats.get('density', 0):.2f} (how connected functions are on average)\n"
        f"Intra-file: {stats.get('intra_edges', '?')} (similar functions in the same file)\n"
        f"Cross-file: {stats.get('inter_edges', '?')} (similar functions across different files)\n"
        f"Isolated: {stats.get('isolated', 0)} (no similar counterparts found)"
    )
    if loc_filtered:
        graph_text += f"\nExcluded by LOC threshold: {loc_filtered}"
    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": graph_text}})

    # Embedding health — code and description
    failed = emb.get("failed_total", emb.get("context_overflow", 0) + emb.get("error", 0))
    desc_failed = desc.get("invalid_json", 0) + desc.get("timeout", 0) + desc.get("error", 0)
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Embedding*\n"
                f"Code — OK: {emb.get('ok', '?')}   Failed: {failed}\n"
                f"  Too large to embed: {emb.get('context_overflow', 0)}\n"
                f"  Error: {emb.get('error', 0)}\n"
                f"Descriptions — OK: {desc.get('ok', '?')}   Failed: {desc_failed}"
            ),
        },
    })

    # Similarity bands — keys match the JSON export format (gt_0.95, b_0.9_0.95, etc.)
    total_fns = stats.get("total_functions") or 0

    def _pct(n: int) -> str:
        return f" ({n / total_fns:.1%})" if total_fns else ""

    gt95 = sim.get("gt_0.95", 0)
    b90_95 = sim.get("b_0.9_0.95", 0)
    b80_90 = sim.get("b_0.8_0.9", 0)
    lt80 = sim.get("lt_0.8", 0)
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Similarity*\n"
                f">0.95 (near-identical): {gt95}{_pct(gt95)}\n"
                f"0.90–0.95 (highly similar): {b90_95}{_pct(b90_95)}\n"
                f"0.80–0.90 (similar): {b80_90}{_pct(b80_90)}\n"
                f"≤0.80 (low similarity): {lt80}{_pct(lt80)}"
            ),
        },
    })

    # Delta since previous run (omit if no previous report)
    if delta and delta.get("previous_timestamp"):
        def _fmt(n: int) -> str:
            return f"+{n}" if n >= 0 else str(n)

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Changes since {delta['previous_timestamp']}*\n"
                    f"Functions: {_fmt(delta.get('functions', 0))}\n"
                    f"Edges: {_fmt(delta.get('edges', 0))}\n"
                    f"Clusters: {_fmt(delta.get('clusters', 0))}"
                ),
            },
        })

    # Duplication clusters (omit if empty)
    if clusters:
        cluster_lines = [f"*Duplication clusters: {len(clusters)}*"]
        for c in clusters[:top_n]:
            cluster_lines.append(
                f"• {c.get('representative', '?')}  ·  {c.get('size', '?')} functions, avg similarity {c.get('avg_score', 0):.3f}"
            )
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(cluster_lines)},
        })

    # Raised flags — one flag per line (omit block if none)
    raised = []
    for flag, label in _FLAG_LABELS.items():
        if flags_raw.get(flag):
            raised.append(label)
    test_poll = flags_raw.get("TEST_POLLUTION")
    if isinstance(test_poll, int) and test_poll > 0:
        raised.append("Test pollution — test code leaked into the similarity graph")
    god_files = flags_raw.get("GOD_FILE")
    if god_files:
        raised.append(f"God files ({len(god_files)}) — files doing too many things, candidates for splitting")
    low_coh = flags_raw.get("LOW_COHESION")
    if low_coh:
        raised.append(f"Low cohesion ({len(low_coh)}) — files where functions don't belong together")

    blocks.append({"type": "divider"})
    if raised:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Flags*\n\U0001f6a8 " + "\n\U0001f6a8 ".join(raised),
            },
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Flags*\n✅ No flags raised"},
        })

    # Top pairs (omit if empty)
    if top_pairs:
        pair_lines = ["*Top pairs*"]
        for pair in top_pairs[:top_n]:
            pair_lines.append(
                f"• {pair.get('a_name', '?')} ↔ {pair.get('b_name', '?')}  ·  {pair.get('score', 0):.4f}"
            )
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(pair_lines)},
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
    reporter_cfg: ReporterConfig | None = None,
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
        repo_label = report_path.parent.parent.name if report_path is not None else "unknown"

        if not success:
            await client.chat_postMessage(
                channel=channel,
                text=f"❌ Report ({repo_label}) at {time_str} — failed: {error or 'unknown error'}",
            )
            return

        blocks = None
        report_data: dict = {}
        if report_path is not None:
            json_path = report_path.with_suffix(".json")
            if json_path.exists():
                try:
                    report_data = json.loads(json_path.read_text())
                    repo_label = report_data.get("repo", repo_label)
                    blocks = _build_report_blocks(report_data, reporter_cfg)
                except Exception:
                    logger.warning("Could not parse report.json for Block Kit; falling back to plain text")

        total_fns = report_data.get("stats", {}).get("total_functions", "?")
        flags_raw = report_data.get("flags", {})
        flag_count = sum([
            bool(flags_raw.get("HIGH_DUPLICATION_CLUSTER")),
            bool(flags_raw.get("CROSS_FILE_DUPLICATION")),
            bool(flags_raw.get("ARCHITECTURE_COUPLING")),
            isinstance(flags_raw.get("TEST_POLLUTION"), int) and flags_raw["TEST_POLLUTION"] > 0,
            bool(flags_raw.get("GOD_FILE")),
            bool(flags_raw.get("LOW_COHESION")),
        ])
        flag_str = f"{flag_count} flag{'s' if flag_count != 1 else ''} raised" if flag_count else "no flags"
        preview = f"✅ Report ({repo_label}) — {flag_str}, {total_fns} functions"

        if blocks:
            await client.chat_postMessage(
                channel=channel,
                text=preview,
                blocks=blocks,
            )
        else:
            await client.chat_postMessage(
                channel=channel,
                text=preview,
            )

        if report_path is not None and report_path.exists():
            await client.files_upload_v2(
                channel=channel,
                file=str(report_path),
                filename=report_path.name,
                title=f"Report ({repo_label}) — {time_str}",
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

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    client = AsyncWebClient(token=token)
    try:
        await client.chat_postMessage(
            channel=channel,
            text=f"Scheduled pipeline run queued for *{repo}* — `{cron_expr}` — {now_utc}",
        )
    except Exception:
        logger.exception("Slack scheduled-run notification failed")
