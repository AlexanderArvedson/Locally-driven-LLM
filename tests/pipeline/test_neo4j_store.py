"""Tests for Neo4jStore using a stub async driver.

The stub records all Cypher queries so we can assert correct query structure
without a live Neo4j instance.
"""

import pytest

from src.pipeline.contracts import (
    FunctionRecord,
    Neo4jConfig,
    SimilarityEdge,
)
from src.pipeline.neo4j_store import Neo4jStore


# ---------------------------------------------------------------------------
# Stub driver / session
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


def _make_store(rows_by_query=None) -> tuple[Neo4jStore, _StubDriver]:
    config = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="u", password="p")
    store = Neo4jStore(config)
    driver = _StubDriver(rows_by_query)
    store._driver = driver  # type: ignore[assignment]
    return store, driver


def _make_record(id_: str = "id1") -> FunctionRecord:
    return FunctionRecord(
        id=id_,
        repo="repo",
        language="python",
        file_path="foo.py",
        function_name="foo",
        qualified_name="foo",
        class_name=None,
        start_line=1,
        end_line=3,
        source_code="def foo(): pass",
        source_hash="abc",
        code_embedding=[0.1, 0.2, 0.3],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_schema_creates_constraint_and_indexes():
    store, driver = _make_store()
    await store.ensure_schema()

    all_queries = [q for s in driver.sessions for q in s.queries]
    combined = " ".join(all_queries)

    assert "CREATE CONSTRAINT function_id_unique" in combined
    assert "function_repo_index" in combined
    assert "function_file_path_index" in combined
    assert "function_name_index" in combined


@pytest.mark.asyncio
async def test_ensure_schema_with_dim_creates_vector_indexes():
    store, driver = _make_store()
    await store.ensure_schema(vector_dim=768)

    all_queries = [q for s in driver.sessions for q in s.queries]
    combined = " ".join(all_queries)

    assert "function_code_embedding_index" in combined
    assert "function_desc_embedding_index" in combined
    assert "768" in combined


@pytest.mark.asyncio
async def test_upsert_functions_batch_uses_unwind():
    store, driver = _make_store()
    store._vector_dim = 3  # skip lazy init

    records = [_make_record("id1"), _make_record("id2")]
    await store.upsert_functions_batch(records)

    all_queries = [q for s in driver.sessions for q in s.queries]
    assert any("UNWIND" in q and "MERGE" in q for q in all_queries)


@pytest.mark.asyncio
async def test_get_existing_hashes_filters_by_repo():
    from src.pipeline.neo4j_store import _GET_HASHES

    rows = [{"id": "id1", "sourceHash": "hash1"}, {"id": "id2", "sourceHash": "hash2"}]
    store, driver = _make_store({_GET_HASHES.strip(): rows})

    hashes = await store.get_existing_hashes("my-repo")

    assert hashes == {"id1": "hash1", "id2": "hash2"}


@pytest.mark.asyncio
async def test_soft_delete_passes_seen_ids():
    from src.pipeline.neo4j_store import _SOFT_DELETE

    rows = [{"deleted": 2}]
    store, driver = _make_store({_SOFT_DELETE.strip(): rows})

    deleted = await store.soft_delete_missing("repo", {"id1", "id2"})

    assert deleted == 2

    all_params = [p for s in driver.sessions for p in s.params_log]
    delete_params = [p for p in all_params if "seen_ids" in p]
    assert delete_params


@pytest.mark.asyncio
async def test_upsert_similarity_edges_uses_unwind():
    store, driver = _make_store()

    edges = [
        SimilarityEdge(source_id="a", target_id="b", code_similarity=0.9, description_similarity=0.0, combined_similarity=0.9),
    ]
    await store.upsert_similarity_edges_batch(edges)

    all_queries = [q for s in driver.sessions for q in s.queries]
    assert any("UNWIND" in q and "SIMILAR_TO" in q for q in all_queries)
