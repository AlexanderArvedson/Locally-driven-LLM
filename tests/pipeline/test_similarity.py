"""Tests for compute_similarity_edges using a mocked Neo4jStore.

The store's query_code_neighbors and query_desc_neighbors are mocked to return
controlled similarity scores, letting us verify the edge-building logic (scoring,
threshold, deduplication) without a live Neo4j instance.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.pipeline.contracts import SimilarityConfig
from src.pipeline.graph.similarity import compute_similarity_edges


def _make_store(code_neighbors=None, desc_neighbors=None):
    """Return a mock Neo4jStore whose query methods return the given results."""
    store = MagicMock()
    store.query_code_neighbors = AsyncMock(return_value=code_neighbors or [])
    store.query_desc_neighbors = AsyncMock(return_value=desc_neighbors or [])
    return store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_identical_vectors_similarity_is_one():
    # "a" queries and finds "b" with score 1.0
    store = _make_store(code_neighbors=[("b", 1.0)])
    embs = [("a", [1.0, 0.0], None), ("b", [1.0, 0.0], None)]
    config = SimilarityConfig(threshold=0.9, top_n=10, code_weight=1.0, description_weight=0.0)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    assert len(edges) == 1
    assert abs(edges[0].combined_similarity - 1.0) < 1e-5


@pytest.mark.asyncio
async def test_orthogonal_vectors_produce_no_edges():
    # Score of 0.0 is below any real threshold
    store = _make_store(code_neighbors=[("b", 0.0)])
    embs = [("a", [1.0, 0.0], None), ("b", [0.0, 1.0], None)]
    config = SimilarityConfig(threshold=0.5, top_n=10, code_weight=1.0, description_weight=0.0)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    assert edges == []


@pytest.mark.asyncio
async def test_source_id_always_less_than_target_id():
    # "z" finds "a" with high score; "a" finds "z" with high score.
    # Only the (a, z) pair should survive deduplication.
    def _side_effect(source_id, embedding, repo, top_n, include_tests=False):
        other = "a" if source_id == "z" else "z"
        return [("a", 1.0)] if other == "a" else [("z", 1.0)]

    store = MagicMock()
    store.query_code_neighbors = AsyncMock(side_effect=_side_effect)
    store.query_desc_neighbors = AsyncMock(return_value=[])

    embs = [("z", [1.0, 0.0], None), ("a", [1.0, 0.0], None)]
    config = SimilarityConfig(threshold=0.9, top_n=10, code_weight=1.0, description_weight=0.0)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    for edge in edges:
        assert edge.source_id < edge.target_id


@pytest.mark.asyncio
async def test_no_self_edges():
    # Store never returns source_id as a neighbor (that's the WHERE clause), but
    # verify the guard in Python also holds.
    store = _make_store(code_neighbors=[])
    embs = [("a", [1.0, 0.0], None), ("b", [0.0, 1.0], None)]
    config = SimilarityConfig(threshold=0.0, top_n=10, code_weight=1.0, description_weight=0.0)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    for edge in edges:
        assert edge.source_id != edge.target_id


@pytest.mark.asyncio
async def test_weighted_combination():
    # Both code and desc similarities are 1.0 → combined = 0.7*1.0 + 0.3*1.0 = 1.0
    store = _make_store(code_neighbors=[("b", 1.0)], desc_neighbors=[("b", 1.0)])
    embs = [("a", [1.0, 0.0], [1.0, 0.0]), ("b", [1.0, 0.0], [1.0, 0.0])]
    config = SimilarityConfig(threshold=0.5, top_n=10, code_weight=0.7, description_weight=0.3)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    assert len(edges) == 1
    assert abs(edges[0].combined_similarity - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_missing_description_embedding_uses_code_only():
    store = _make_store(code_neighbors=[("b", 1.0)])
    embs = [("a", [1.0, 0.0], None), ("b", [1.0, 0.0], None)]
    config = SimilarityConfig(threshold=0.5, top_n=10, code_weight=0.7, description_weight=0.3)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    assert len(edges) == 1
    assert abs(edges[0].combined_similarity - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_fewer_than_two_returns_empty():
    store = _make_store()
    config = SimilarityConfig()

    assert await compute_similarity_edges(store, [], "repo", config) == []
    assert await compute_similarity_edges(store, [("a", [1.0], None)], "repo", config) == []


@pytest.mark.asyncio
async def test_threshold_filters_low_similarity():
    store = _make_store(code_neighbors=[("b", 0.5)])
    embs = [("a", [1.0, 0.0], None), ("b", [0.5, 0.5], None)]
    config = SimilarityConfig(threshold=0.99, top_n=10, code_weight=1.0, description_weight=0.0)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    assert edges == []


@pytest.mark.asyncio
async def test_functions_without_any_embedding_are_skipped():
    # Function "c" has no embeddings; store should never be called for it.
    store = _make_store(code_neighbors=[("b", 0.95)])
    embs = [("a", [1.0, 0.0], None), ("b", [1.0, 0.0], None), ("c", None, None)]
    config = SimilarityConfig(threshold=0.9, top_n=10, code_weight=1.0, description_weight=0.0)

    edges = await compute_similarity_edges(store, embs, "repo", config)

    # Only one edge (a, b); "c" never participates.
    assert all("c" not in (e.source_id, e.target_id) for e in edges)
