"""Unit tests for SlackNotifier.

Uses a mocked AsyncWebClient to verify Slack API calls without
requiring real credentials or a live Slack workspace.
"""

from __future__ import annotations

import datetime
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.api.slack_notifier import SlackNotifier, _fmt_duration, _fmt_eta
from src.git.branch_manager import SyncResult
from src.pipeline.contracts import PipelineResult, SlackPipelineConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _notifier(
    enabled: bool = True,
    debug: bool = False,
    embed_interval: int = 10,
    describe_interval: int = 10,
) -> SlackNotifier:
    return SlackNotifier(
        SlackPipelineConfig(
            enabled=enabled,
            debug_messages=debug,
            embed_progress_interval=embed_interval,
            describe_progress_interval=describe_interval,
        )
    )


def _mock_client(ts: str = "1234.5678") -> AsyncMock:
    client = AsyncMock()
    client.chat_postMessage.return_value = {"ts": ts}
    client.chat_update.return_value = {}
    return client


def _blocks_text(call_kwargs: dict) -> str:
    """Extract all text values from a Block Kit blocks list into a single string."""
    parts = []
    for block in call_kwargs.get("blocks", []):
        text = block.get("text", {})
        if isinstance(text, dict):
            v = text.get("text", "")
            if v:
                parts.append(v)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# _fmt_duration
# ---------------------------------------------------------------------------


def test_fmt_duration_seconds():
    assert _fmt_duration(45) == "45s"


def test_fmt_duration_minutes():
    assert _fmt_duration(192) == "3m 12s"


def test_fmt_duration_hours():
    assert _fmt_duration(4335) == "1h 12m"


# ---------------------------------------------------------------------------
# _fmt_eta
# ---------------------------------------------------------------------------


def test_fmt_eta_appends_remaining():
    assert "remaining" in _fmt_eta(120)


# ---------------------------------------------------------------------------
# pipeline_start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_start_posts_to_channel():
    n = _notifier()
    client = _mock_client(ts="111.222")
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        n._client = client
        n._channel = "#pipe"
        await n.pipeline_start("my-repo")
    client.chat_postMessage.assert_called_once()
    call_kwargs = client.chat_postMessage.call_args.kwargs
    assert "my-repo" in call_kwargs["text"]
    assert n._thread_ts == "111.222"
    assert n._message_ts == "111.222"


@pytest.mark.asyncio
async def test_pipeline_start_noop_when_disabled():
    n = _notifier(enabled=False)
    client = _mock_client()
    n._client = client
    await n.pipeline_start("repo")
    client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_start_noop_when_no_env_vars():
    n = _notifier()
    with patch.dict("os.environ", {}, clear=True):
        await n.pipeline_start("repo")
    assert n._thread_ts is None


# ---------------------------------------------------------------------------
# pipeline_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_complete_updates_original_message():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    n._message_ts = "111.222"
    result = PipelineResult(changed=5, edges_written=20, duration_seconds=90.0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.pipeline_complete(result)
    client.chat_update.assert_called_once()
    update_kwargs = client.chat_update.call_args.kwargs
    assert update_kwargs["ts"] == "111.222"
    assert "complete" in update_kwargs["text"].lower()


@pytest.mark.asyncio
async def test_pipeline_complete_posts_thread_summary():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    n._message_ts = "111.222"
    result = PipelineResult(total_extracted=100, changed=10, edges_written=50, duration_seconds=60.0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.pipeline_complete(result)
    # One postMessage call (thread reply with Block Kit summary)
    client.chat_postMessage.assert_called_once()
    call_kwargs = client.chat_postMessage.call_args.kwargs
    # fallback text carries key numbers for notification previews
    assert "100" in call_kwargs["text"]   # total_extracted
    assert "50" in call_kwargs["text"]    # edges_written
    # blocks are present
    assert "blocks" in call_kwargs


# ---------------------------------------------------------------------------
# pipeline_failed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_failed_updates_original_message():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    n._message_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.pipeline_failed("Connection refused")
    client.chat_update.assert_called_once()
    assert "failed" in client.chat_update.call_args.kwargs["text"].lower()


@pytest.mark.asyncio
async def test_pipeline_failed_posts_reason_to_thread():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    n._message_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.pipeline_failed("Connection refused")
    text = _blocks_text(client.chat_postMessage.call_args.kwargs)
    assert "Connection refused" in text


# ---------------------------------------------------------------------------
# sync_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_complete_clone_success():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    result = SyncResult(operation="clone", success=True, branch="main", commit_hash="abc1234")
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.sync_complete(result)
    combined = "\n".join(_blocks_text(call.kwargs) for call in client.chat_postMessage.call_args_list)
    assert "Clone" in combined
    assert "main" in combined
    assert "abc1234" in combined
    assert "Cloned" in combined


@pytest.mark.asyncio
async def test_sync_complete_pull_already_up_to_date():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    result = SyncResult(operation="pull", success=True, branch="main", commit_hash="def5678", already_up_to_date=True)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.sync_complete(result)
    texts = "\n".join(_blocks_text(call.kwargs) for call in client.chat_postMessage.call_args_list)
    assert "up to date" in texts.lower()


@pytest.mark.asyncio
async def test_sync_complete_pull_failed():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    result = SyncResult(operation="pull", success=False, branch="main", commit_hash=None, error="Authentication failed")
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.sync_complete(result)
    texts = "\n".join(_blocks_text(call.kwargs) for call in client.chat_postMessage.call_args_list)
    assert "Authentication failed" in texts
    assert "failed" in texts.lower()


@pytest.mark.asyncio
async def test_sync_complete_debug_posts_detail():
    n = _notifier(debug=True)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    result = SyncResult(operation="clone", success=True, branch="main", commit_hash="abc1234")
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.sync_complete(result)
    # debug=True should include "Starting repository clone" detail message
    texts = "\n".join(call.kwargs["text"] for call in client.chat_postMessage.call_args_list)
    assert "clone" in texts.lower()


@pytest.mark.asyncio
async def test_sync_complete_no_debug_skips_detail():
    n = _notifier(debug=False)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    result = SyncResult(operation="pull", success=True, branch="main", commit_hash="aaa0000")
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.sync_complete(result)
    # Should only post the outcome card, not the "Local repository found" detail
    assert client.chat_postMessage.call_count == 1


# ---------------------------------------------------------------------------
# sync_start
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_start_noop_when_debug_false():
    n = _notifier(debug=False)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    await n.sync_start()
    client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_sync_start_posts_when_debug_true():
    n = _notifier(debug=True)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.sync_start()
    client.chat_postMessage.assert_called_once()


# ---------------------------------------------------------------------------
# progress throttling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_posts_at_interval():
    n = _notifier(embed_interval=10)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    t0 = time.monotonic() - 5  # simulate 5 seconds elapsed
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.progress("Code embedding", 10, 100, t0)
    client.chat_postMessage.assert_called_once()
    text = _blocks_text(client.chat_postMessage.call_args.kwargs)
    assert "10" in text
    assert "100" in text
    assert "10.0%" in text


@pytest.mark.asyncio
async def test_progress_skips_between_intervals():
    n = _notifier(embed_interval=10)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    t0 = time.monotonic() - 1
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.progress("Code embedding", 5, 100, t0)   # not a multiple of 10
        await n.progress("Code embedding", 7, 100, t0)   # not a multiple of 10
    client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_progress_noop_when_disabled():
    n = _notifier(enabled=False, embed_interval=1)
    client = _mock_client()
    n._client = client
    await n.progress("Code embedding", 1, 10, time.monotonic())
    client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_progress_embed_stage_uses_embed_interval():
    """Code embedding hits at embed_progress_interval, not describe_progress_interval."""
    n = _notifier(embed_interval=5, describe_interval=100)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    t0 = time.monotonic() - 1
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.progress("Code embedding", 5, 100, t0)   # multiple of embed_interval=5
    client.chat_postMessage.assert_called_once()


@pytest.mark.asyncio
async def test_progress_describe_stage_uses_describe_interval():
    """Description generation hits at describe_progress_interval, not embed_progress_interval."""
    n = _notifier(embed_interval=100, describe_interval=5)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    t0 = time.monotonic() - 1
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.progress("Description generation", 5, 100, t0)   # multiple of describe_interval=5
    client.chat_postMessage.assert_called_once()


# ---------------------------------------------------------------------------
# stage summaries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extraction_complete_includes_counts():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.extraction_complete(files=50, functions=1200, duration=12.5)
    text = _blocks_text(client.chat_postMessage.call_args.kwargs)
    assert "50" in text
    assert "1,200" in text


@pytest.mark.asyncio
async def test_embedding_complete_includes_stage_label():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.embedding_complete(generated=990, failures=10, duration=120.0, stage="code")
    text = _blocks_text(client.chat_postMessage.call_args.kwargs)
    assert "Code embeddings" in text
    assert "990" in text
    assert "10" in text


@pytest.mark.asyncio
async def test_description_complete_includes_skipped():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.description_complete(generated=800, skipped=50, duration=300.0)
    text = _blocks_text(client.chat_postMessage.call_args.kwargs)
    assert "800" in text
    assert "50" in text


@pytest.mark.asyncio
async def test_similarity_complete_includes_relationship_count():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.similarity_complete(relationships=4200, duration=45.0)
    text = _blocks_text(client.chat_postMessage.call_args.kwargs)
    assert "4,200" in text


# ---------------------------------------------------------------------------
# report_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_complete_failure_posts_error():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    started = datetime.datetime(2026, 6, 10, 9, 0, 0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.report_complete(False, started, None, "Permission denied")
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "Permission denied" in text
    assert "❌" in text


@pytest.mark.asyncio
async def test_report_complete_success_posts_preview():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    started = datetime.datetime(2026, 6, 10, 9, 0, 0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.report_complete(True, started, None, None)
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "✅" in text
    assert "Report" in text


@pytest.mark.asyncio
async def test_report_complete_posts_to_channel_even_when_thread_ts_set():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    n._thread_ts = "111.222"
    started = datetime.datetime(2026, 6, 10, 9, 0, 0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.report_complete(True, started, None, None)
    call_kwargs = client.chat_postMessage.call_args.kwargs
    assert "thread_ts" not in call_kwargs


@pytest.mark.asyncio
async def test_report_complete_posts_to_channel_when_no_thread():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    # thread_ts is None (standalone /report run)
    started = datetime.datetime(2026, 6, 10, 9, 0, 0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.report_complete(True, started, None, None)
    call_kwargs = client.chat_postMessage.call_args.kwargs
    assert "thread_ts" not in call_kwargs


@pytest.mark.asyncio
async def test_report_complete_fires_when_slack_enabled_false():
    # report_complete is not gated by self._enabled
    n = _notifier(enabled=False)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    started = datetime.datetime(2026, 6, 10, 9, 0, 0)
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.report_complete(True, started, None, None)
    client.chat_postMessage.assert_called_once()


# ---------------------------------------------------------------------------
# scheduled_run_queued
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduled_run_queued_posts_repo_name():
    n = _notifier()
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.scheduled_run_queued("my-repo")
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "my-repo" in text
    assert "⏰" in text


@pytest.mark.asyncio
async def test_scheduled_run_queued_fires_when_slack_enabled_false():
    # scheduled_run_queued is not gated by self._enabled
    n = _notifier(enabled=False)
    client = _mock_client()
    n._client = client
    n._channel = "#pipe"
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test", "SLACK_NOTIFY_CHANNEL": "#pipe"}):
        await n.scheduled_run_queued("my-repo")
    client.chat_postMessage.assert_called_once()


@pytest.mark.asyncio
async def test_scheduled_run_queued_noop_without_env_vars():
    n = _notifier()
    with patch.dict("os.environ", {}, clear=True):
        await n.scheduled_run_queued("my-repo")  # must not raise
