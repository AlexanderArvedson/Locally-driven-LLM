"""Unified Slack notifications for all pipeline events.

SlackNotifier is the single entry point for all Slack communication:
- Thread-based progress tracking during a pipeline run (start, stages, progress)
- Report summary and file upload after a run or on-demand
- Scheduled-run notices from the cron trigger

Thread strategy: pipeline_start() posts to the channel and stores thread_ts.
All stage/progress updates are posted as thread replies. pipeline_complete()
and pipeline_failed() also update the original channel message via chat_update.
report_complete() always posts directly to the channel as a standalone message,
appearing below the pipeline thread regardless of whether a thread is active.

All methods are fire-and-forget: Slack errors are swallowed so a Slack outage
never affects pipeline execution.
"""

from __future__ import annotations

import datetime
import json
import os
import time
from pathlib import Path

from loguru import logger
from slack_sdk.web.async_client import AsyncWebClient

from src.git.branch_manager import SyncResult
from src.pipeline.contracts import PipelineResult, ReporterConfig, SlackPipelineConfig


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

    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"\U0001f4ca {data.get('repo', '?')} — {data.get('timestamp', '?')}"},
    })

    if summary:
        bullets = "\n".join(
            f"• {s.rstrip('.')}." for s in summary.split(". ") if s.strip()
        )
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary*\n{bullets}"},
        })

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

    gt95 = sim.get("gt_0.95", 0)
    b90_95 = sim.get("b_0.9_0.95", 0)
    b80_90 = sim.get("b_0.8_0.9", 0)
    lt80 = sim.get("lt_0.8", 0)
    total_edges = gt95 + b90_95 + b80_90 + lt80

    def _pct(n: int) -> str:
        return f" ({n / total_edges:.1%})" if total_edges else ""

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Similarity*\n"
                f"≥0.95 (near-identical): {gt95}{_pct(gt95)}\n"
                f"0.90–0.95 (highly similar): {b90_95}{_pct(b90_95)}\n"
                f"0.80–0.90 (similar): {b80_90}{_pct(b80_90)}\n"
                f"≤0.80 (low similarity): {lt80}{_pct(lt80)}"
            ),
        },
    })

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


class SlackNotifier:
    """Unified Slack notifier for all pipeline events, reports, and schedule notices.

    Create one instance per pipeline run and pass it to both EmbeddingPipeline
    and the report handler so that report summaries are posted to the same thread
    as the pipeline progress updates.
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
        """Return a configured client, or None if Slack env vars are absent."""
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        channel = os.environ.get("SLACK_NOTIFY_CHANNEL", "")
        if not token or not channel:
            return None
        self._channel = channel
        if self._client is None:
            self._client = AsyncWebClient(token=token)
        return self._client

    async def _reply(self, text: str) -> None:
        """Post text as a thread reply, or directly to the channel if no thread is active."""
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

    # -------------------------------------------------------------------------
    # Pipeline lifecycle
    # -------------------------------------------------------------------------

    async def pipeline_start(self, repo: str) -> None:
        """Post the initial channel message and store thread_ts for all subsequent replies."""
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
                    text="❌ Pipeline failed",
                )
            await self._reply(f"❌ Pipeline failed.\n\nReason:\n{error}")
        except Exception:
            logger.exception("Slack pipeline_failed notification failed")

    # -------------------------------------------------------------------------
    # Sync stage
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Pipeline stages
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Report
    # -------------------------------------------------------------------------

    async def report_complete(
        self,
        success: bool,
        started_at: datetime.datetime,
        report_path: Path | None,
        error: str | None,
        reporter_cfg: ReporterConfig | None = None,
    ) -> None:
        """Post a Block Kit report summary and upload the .md file.

        Always posts directly to the channel as a standalone message so it appears
        below the pipeline thread. File uploads also go to the channel.
        Not gated by self._enabled — report notifications fire regardless of
        pipeline progress config.
        """
        client = self._get_client()
        if client is None:
            return

        time_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
        try:
            repo_label = report_path.parent.parent.name if report_path is not None else "unknown"

            if not success:
                await self._reply(
                    f"❌ Report ({repo_label}) at {time_str} — failed: {error or 'unknown error'}"
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

            post_kwargs: dict = {"channel": self._channel, "text": preview}
            if blocks:
                post_kwargs["blocks"] = blocks
            await client.chat_postMessage(**post_kwargs)

            if report_path is not None and report_path.exists():
                await client.files_upload_v2(
                    channel=self._channel,
                    file=str(report_path),
                    filename=report_path.name,
                    title=f"Report ({repo_label}) — {time_str}",
                )
        except Exception:
            logger.exception("Slack report notification failed")

    # -------------------------------------------------------------------------
    # Scheduled run
    # -------------------------------------------------------------------------

    async def scheduled_run_queued(self, repo: str) -> None:
        """Post a notice that a cron-triggered pipeline run has been queued.

        Not gated by self._enabled — schedule notices fire regardless of
        pipeline progress config.
        """
        client = self._get_client()
        if client is None:
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        try:
            await client.chat_postMessage(
                channel=self._channel,
                text=f"⏰ Scheduled pipeline run queued for *{repo}* — {now_utc}",
            )
        except Exception:
            logger.exception("Slack scheduled-run notification failed")
