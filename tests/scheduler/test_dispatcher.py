"""Unit tests for TaskDispatcher.

All external I/O (OllamaClient, Neo4jStore, EmbeddingPipeline, httpx) is
mocked so these tests run without a live Ollama server or Neo4j instance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.contracts import (
    BatchSizeConfig,
    ConcurrencyConfig,
    LimitsConfig,
    Neo4jConfig,
    PipelineConfig,
    PipelineResult,
    ReporterConfig,
    SimilarityConfig,
)
from src.pipeline.query import QueryMatch, QueryResult
from src.scheduler.dispatcher import TaskDispatcher
from src.scheduler.task import PipelineTask, QueryTask, ReportTask


pytestmark = pytest.mark.asyncio


def _make_pipeline_config() -> PipelineConfig:
    return PipelineConfig(
        repo_path="/tmp/repo",
        repo_name="myrepo",
        supported_languages=["python"],
        ignore_paths=[],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="llama3",
        describer_model="llama3",
        similarity=SimilarityConfig(),
        neo4j=Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="test"),
        concurrency=ConcurrencyConfig(),
        batch_sizes=BatchSizeConfig(),
        limits=LimitsConfig(),
        reporter=ReporterConfig(),
    )


def _make_query_match(name: str, score: float, path: str) -> QueryMatch:
    return QueryMatch(
        function_name=name.rsplit(".", 1)[-1],
        qualified_name=name,
        file_path=path,
        score=score,
        description=None,
    )


# ---------------------------------------------------------------------------
# _handle_query tests
# ---------------------------------------------------------------------------


async def test_handle_query_posts_results_to_response_url(monkeypatch):
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    matches = [
        _make_query_match("auth.verify_token", 0.94, "src/auth/service.py"),
        _make_query_match("jwt.validate", 0.91, "src/middleware/jwt.py"),
    ]
    fake_result = QueryResult(query="find auth functions", matches=matches, index_used="both")

    mock_client = AsyncMock()
    mock_store = AsyncMock()
    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr("httpx.AsyncClient", lambda: mock_http_client)

    with (
        patch("src.core.ollama_client.OllamaClient", return_value=mock_client),
        patch("src.pipeline.graph.store.Neo4jStore", return_value=mock_store),
        patch("src.pipeline.query.search", AsyncMock(return_value=fake_result)),
    ):
        task = QueryTask(
            id="q1",
            query_text="find auth functions",
            response_url="http://slack.example.com/response",
            repo="myrepo",
        )
        await dispatcher.execute(task)

    mock_http_client.post.assert_called_once()
    url, *_ = mock_http_client.post.call_args.args
    assert url == "http://slack.example.com/response"

    payload = mock_http_client.post.call_args.kwargs["json"]
    assert "find auth functions" in payload["text"]
    assert "auth.verify_token" in payload["text"]
    assert "0.94" in payload["text"]

    mock_client.close.assert_called_once()
    mock_store.close.assert_called_once()


async def test_handle_query_posts_error_message_on_search_failure(monkeypatch):
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_client = AsyncMock()
    mock_store = AsyncMock()
    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr("httpx.AsyncClient", lambda: mock_http_client)

    with (
        patch("src.core.ollama_client.OllamaClient", return_value=mock_client),
        patch("src.pipeline.graph.store.Neo4jStore", return_value=mock_store),
        patch("src.pipeline.query.search", AsyncMock(side_effect=RuntimeError("Neo4j unavailable"))),
    ):
        task = QueryTask(
            id="q2",
            query_text="find auth functions",
            response_url="http://slack.example.com/response",
            repo="myrepo",
        )
        await dispatcher.execute(task)

    payload = mock_http_client.post.call_args.kwargs["json"]
    assert "Search failed" in payload["text"]
    assert "Neo4j unavailable" in payload["text"]

    # Resources must be released even when search() raises.
    mock_client.close.assert_called_once()
    mock_store.close.assert_called_once()


async def test_handle_query_returns_no_results_message_when_empty(monkeypatch):
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    empty_result = QueryResult(query="nothing here", matches=[], index_used="both")

    mock_client = AsyncMock()
    mock_store = AsyncMock()
    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr("httpx.AsyncClient", lambda: mock_http_client)

    with (
        patch("src.core.ollama_client.OllamaClient", return_value=mock_client),
        patch("src.pipeline.graph.store.Neo4jStore", return_value=mock_store),
        patch("src.pipeline.query.search", AsyncMock(return_value=empty_result)),
    ):
        task = QueryTask(
            id="q3",
            query_text="nothing here",
            response_url="http://slack.example.com/response",
            repo="myrepo",
        )
        await dispatcher.execute(task)

    payload = mock_http_client.post.call_args.kwargs["json"]
    assert "No results" in payload["text"]


# ---------------------------------------------------------------------------
# _handle_pipeline tests
# ---------------------------------------------------------------------------


async def test_handle_pipeline_runs_pipeline_and_closes_it():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value=PipelineResult())
    mock_pipeline.close = AsyncMock()

    with (
        patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline),
        patch("src.api.slack_notifier.notify_pipeline_result", AsyncMock()),
        patch.object(dispatcher, "_handle_report", AsyncMock()),
    ):
        task = PipelineTask(id="p1", repo="myrepo")
        await dispatcher.execute(task)

    mock_pipeline.run.assert_called_once()
    mock_pipeline.close.assert_called_once()


async def test_handle_pipeline_closes_pipeline_even_on_failure():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(side_effect=RuntimeError("pipeline boom"))
    mock_pipeline.close = AsyncMock()

    with patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline):
        task = PipelineTask(id="p2", repo="myrepo")
        with pytest.raises(RuntimeError, match="pipeline boom"):
            await dispatcher.execute(task)

    mock_pipeline.close.assert_called_once()


async def test_handle_pipeline_passes_no_descriptions_flag():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value=PipelineResult())
    mock_pipeline.close = AsyncMock()

    with (
        patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline) as mock_cls,
        patch("src.api.slack_notifier.notify_pipeline_result", AsyncMock()),
        patch.object(dispatcher, "_handle_report", AsyncMock()),
    ):
        task = PipelineTask(id="p3", repo="myrepo", no_descriptions=True)
        await dispatcher.execute(task)

    _, kwargs = mock_cls.call_args
    assert kwargs.get("skip_descriptions") is True


async def test_handle_pipeline_chains_report_by_default():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value=PipelineResult(loc_filtered=3))
    mock_pipeline.close = AsyncMock()
    mock_handle_report = AsyncMock()

    with (
        patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline),
        patch("src.api.slack_notifier.notify_pipeline_result", AsyncMock()),
        patch.object(dispatcher, "_handle_report", mock_handle_report),
    ):
        task = PipelineTask(id="p4", repo="myrepo")
        await dispatcher.execute(task)

    mock_handle_report.assert_called_once()
    report_task = mock_handle_report.call_args.args[0]
    assert isinstance(report_task, ReportTask)
    assert report_task.repo == "myrepo"
    assert report_task.loc_filtered == 3


async def test_handle_pipeline_skips_report_with_no_report_flag():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value=PipelineResult())
    mock_pipeline.close = AsyncMock()
    mock_handle_report = AsyncMock()

    with (
        patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline),
        patch("src.api.slack_notifier.notify_pipeline_result", AsyncMock()),
        patch.object(dispatcher, "_handle_report", mock_handle_report),
    ):
        task = PipelineTask(id="p5", repo="myrepo", no_report=True)
        await dispatcher.execute(task)

    mock_handle_report.assert_not_called()


async def test_handle_pipeline_skips_report_on_dry_run():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    mock_pipeline = AsyncMock()
    mock_pipeline.run = AsyncMock(return_value=PipelineResult())
    mock_pipeline.close = AsyncMock()
    mock_handle_report = AsyncMock()

    with (
        patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline),
        patch("src.api.slack_notifier.notify_pipeline_result", AsyncMock()),
        patch.object(dispatcher, "_handle_report", mock_handle_report),
    ):
        task = PipelineTask(id="p6", repo="myrepo", dry_run=True)
        await dispatcher.execute(task)

    mock_handle_report.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_report tests
# ---------------------------------------------------------------------------


async def test_execute_dispatches_report_task():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())
    mock_handle_report = AsyncMock()

    with patch.object(dispatcher, "_handle_report", mock_handle_report):
        task = ReportTask(id="r1", repo="myrepo")
        await dispatcher.execute(task)

    mock_handle_report.assert_called_once_with(task)


async def test_handle_report_calls_generate_report_and_notifies():
    dispatcher = TaskDispatcher(pipeline_config=_make_pipeline_config())

    from pathlib import Path
    mock_report_dir = MagicMock()
    mock_report_dir.__truediv__ = lambda self, other: Path("/tmp/report.md")

    with (
        patch("src.pipeline.reporting.reporter.generate_report", AsyncMock(return_value=mock_report_dir)),
        patch("src.api.slack_notifier.notify_report_result", AsyncMock()) as mock_notify,
    ):
        task = ReportTask(id="r2", repo="myrepo", loc_filtered=5)
        await dispatcher.execute(task)

    mock_notify.assert_called_once()
    success, started_at, report_path, error = mock_notify.call_args.args
    assert success is True
    assert error is None
