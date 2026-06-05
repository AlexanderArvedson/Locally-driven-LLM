"""Tests for src/pipeline/query.py.

Uses the same stub-driver pattern as test_neo4j_store.py. OllamaClient.embed
is replaced with AsyncMock so no real Ollama or Neo4j server is required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.ollama_client import EmbedResult, OllamaClient
from src.pipeline.contracts import Neo4jConfig, PipelineConfig, SimilarityConfig
from src.pipeline.neo4j_store import (
    Neo4jStore,
    _GET_FUNCTIONS_BY_IDS,
    _QUERY_CODE_NEIGHBORS,
    _QUERY_DESC_NEIGHBORS,
)
from src.pipeline.query import QueryResult, search


# ---------------------------------------------------------------------------
# Stub driver (mirrors test_neo4j_store.py)
# ---------------------------------------------------------------------------

class _StubResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    async def data(self):
        return self._rows

    async def single(self):
        return self._rows[0] if self._rows else None


class _StubSession:
    def __init__(self, rows_by_query=None):
        self.queries: list[str] = []
        self.params_log: list[dict] = []
        self._rows_by_query = rows_by_query or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def run(self, query: str, **kwargs) -> _StubResult:
        self.queries.append(query.strip())
        self.params_log.append(kwargs)
        rows = self._rows_by_query.get(query.strip(), [])
        return _StubResult(rows)


class _StubDriver:
    def __init__(self, rows_by_query=None):
        self.sessions: list[_StubSession] = []
        self._rows = rows_by_query or {}

    def session(self, **kwargs):
        s = _StubSession(self._rows)
        self.sessions.append(s)
        return s

    async def close(self):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(rows_by_query: dict | None = None) -> Neo4jStore:
    config = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="u", password="p")
    store = Neo4jStore(config)
    store._driver = _StubDriver(rows_by_query)  # type: ignore[assignment]
    return store


def _make_client(embedding: list[float] | None = None) -> OllamaClient:
    """Return a mock OllamaClient whose embed() resolves immediately."""
    vec = embedding or [0.1] * 4
    client = AsyncMock(spec=OllamaClient)
    client.embed.return_value = EmbedResult(embedding=vec)
    return client


def _make_config() -> PipelineConfig:
    return PipelineConfig(
        repo_path="/tmp/repo",
        repo_name="test-repo",
        supported_languages=["python"],
        ignore_paths=[],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="qwen2.5-coder:7b",
        describer_model="qwen2.5-coder:7b",
        similarity=SimilarityConfig(),
        neo4j=Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="u", password="p"),
    )


_FUNCTION_ROWS = {
    "fn1": {"id": "fn1", "qualifiedName": "mod.fn1", "filePath": "mod.py", "description": None},
    "fn2": {"id": "fn2", "qualifiedName": "mod.fn2", "filePath": "mod.py", "description": '{"summary": "does stuff"}'},
    "fn3": {"id": "fn3", "qualifiedName": "svc.MyClass.fn3", "filePath": "svc.py", "description": None},
    "shared": {"id": "shared", "qualifiedName": "shared.fn", "filePath": "shared.py", "description": None},
}


# ---------------------------------------------------------------------------
# Tests: search()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_returns_sorted_matches():
    """Results from both indexes are merged and returned sorted by score descending."""
    rows_by_query = {
        _QUERY_CODE_NEIGHBORS.strip(): [{"id": "fn1", "score": 0.9}, {"id": "fn2", "score": 0.7}],
        _QUERY_DESC_NEIGHBORS.strip(): [{"id": "fn3", "score": 0.85}],
        _GET_FUNCTIONS_BY_IDS.strip(): [_FUNCTION_ROWS["fn1"], _FUNCTION_ROWS["fn3"], _FUNCTION_ROWS["fn2"]],
    }
    store = _make_store(rows_by_query)
    client = _make_client()
    config = _make_config()

    result = await search(store, client, "find auth functions", "test-repo", config, top_n=10)

    assert isinstance(result, QueryResult)
    assert result.query == "find auth functions"
    assert result.index_used == "both"
    assert len(result.matches) == 3
    # Sorted descending by score.
    assert result.matches[0].qualified_name == "mod.fn1"
    assert result.matches[0].score == pytest.approx(0.9)
    assert result.matches[1].qualified_name == "svc.MyClass.fn3"
    assert result.matches[1].score == pytest.approx(0.85)
    assert result.matches[2].qualified_name == "mod.fn2"
    assert result.matches[2].score == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_search_deduplicates_ids_taking_max_score():
    """When the same function id appears in both indexes, only the highest score is kept."""
    rows_by_query = {
        _QUERY_CODE_NEIGHBORS.strip(): [{"id": "shared", "score": 0.8}],
        _QUERY_DESC_NEIGHBORS.strip(): [{"id": "shared", "score": 0.95}],
        _GET_FUNCTIONS_BY_IDS.strip(): [_FUNCTION_ROWS["shared"]],
    }
    store = _make_store(rows_by_query)
    client = _make_client()
    config = _make_config()

    result = await search(store, client, "shared helper", "test-repo", config)

    assert len(result.matches) == 1
    assert result.matches[0].qualified_name == "shared.fn"
    assert result.matches[0].score == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_search_empty_results():
    """Both indexes returning nothing yields an empty match list."""
    rows_by_query: dict = {}
    store = _make_store(rows_by_query)
    client = _make_client()
    config = _make_config()

    result = await search(store, client, "something obscure", "test-repo", config)

    assert result.matches == []
    assert result.query == "something obscure"


@pytest.mark.asyncio
async def test_search_respects_top_n():
    """Only up to top_n results are returned even when more are available."""
    many_code_hits = [{"id": f"fn{i}", "score": 1.0 - i * 0.05} for i in range(20)]
    fn_rows = [
        {"id": f"fn{i}", "qualifiedName": f"mod.fn{i}", "filePath": "mod.py", "description": None}
        for i in range(20)
    ]
    rows_by_query = {
        _QUERY_CODE_NEIGHBORS.strip(): many_code_hits,
        _QUERY_DESC_NEIGHBORS.strip(): [],
        _GET_FUNCTIONS_BY_IDS.strip(): fn_rows,
    }
    store = _make_store(rows_by_query)
    client = _make_client()
    config = _make_config()

    result = await search(store, client, "anything", "test-repo", config, top_n=5)

    assert len(result.matches) == 5
    # Highest-scoring functions are first.
    assert result.matches[0].function_name == "fn0"


@pytest.mark.asyncio
async def test_search_function_name_extracted_from_qualified_name():
    """function_name is the last segment of qualified_name."""
    rows_by_query = {
        _QUERY_CODE_NEIGHBORS.strip(): [{"id": "fn3", "score": 0.88}],
        _QUERY_DESC_NEIGHBORS.strip(): [],
        _GET_FUNCTIONS_BY_IDS.strip(): [_FUNCTION_ROWS["fn3"]],
    }
    store = _make_store(rows_by_query)
    client = _make_client()
    config = _make_config()

    result = await search(store, client, "class method", "test-repo", config)

    assert result.matches[0].qualified_name == "svc.MyClass.fn3"
    assert result.matches[0].function_name == "fn3"


# ---------------------------------------------------------------------------
# Tests: get_functions_by_ids()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_functions_by_ids_returns_rows():
    """get_functions_by_ids passes ids and returns the driver rows unchanged."""
    expected = [
        {"id": "fn1", "qualifiedName": "mod.fn1", "filePath": "mod.py", "description": None},
        {"id": "fn2", "qualifiedName": "mod.fn2", "filePath": "mod.py", "description": "desc"},
    ]
    rows_by_query = {_GET_FUNCTIONS_BY_IDS.strip(): expected}
    store = _make_store(rows_by_query)

    result = await store.get_functions_by_ids(["fn1", "fn2"])

    assert result == expected


@pytest.mark.asyncio
async def test_get_functions_by_ids_empty_list():
    """Calling with an empty id list returns an empty list."""
    store = _make_store()

    result = await store.get_functions_by_ids([])

    assert result == []
