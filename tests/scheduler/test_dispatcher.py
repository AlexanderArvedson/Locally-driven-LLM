"""Unit tests for TaskDispatcher.

All external I/O (OllamaClient, Neo4jStore, EmbeddingPipeline, httpx) is
mocked so these tests run without a live Ollama server or Neo4j instance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.query import QueryMatch, QueryResult
from src.scheduler.dispatcher import TaskDispatcher
from src.scheduler.slack_task import PipelineTask, QueryTask


pytestmark = pytest.mark.asyncio


def _make_pipeline_config() -> MagicMock:
    cfg = MagicMock()
    cfg.embedding_url = "http://localhost:11434"
    return cfg


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
        patch("src.pipeline.neo4j_store.Neo4jStore", return_value=mock_store),
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
        patch("src.pipeline.neo4j_store.Neo4jStore", return_value=mock_store),
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
        patch("src.pipeline.neo4j_store.Neo4jStore", return_value=mock_store),
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
    mock_pipeline.run = AsyncMock(return_value=MagicMock())
    mock_pipeline.close = AsyncMock()

    with patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline):
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
    mock_pipeline.run = AsyncMock(return_value=MagicMock())
    mock_pipeline.close = AsyncMock()

    with patch("src.pipeline.pipeline.EmbeddingPipeline", return_value=mock_pipeline) as mock_cls:
        task = PipelineTask(id="p3", repo="myrepo", no_descriptions=True)
        await dispatcher.execute(task)

    _, kwargs = mock_cls.call_args
    assert kwargs.get("skip_descriptions") is True
