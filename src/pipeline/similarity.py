"""Cosine similarity graph builder using Neo4j HNSW vector indexes.

For each function the code and/or description embedding is used to query the
Neo4j approximate nearest-neighbour index directly, avoiding an n×n in-memory
matrix. Complexity is O(n log n) instead of O(n²), making it practical for
large repos.

Edge count is bounded at roughly n * top_n / 2 by the source_id < target_id
deduplication invariant.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.pipeline.contracts import SimilarityConfig, SimilarityEdge

if TYPE_CHECKING:
    from src.pipeline.neo4j_store import Neo4jStore

_CONCURRENCY = 20


async def compute_similarity_edges(
    store: Neo4jStore,
    embeddings: list[tuple[str, list[float] | None, list[float] | None]],
    repo: str,
    config: SimilarityConfig,
    include_tests: bool = False,
) -> list[SimilarityEdge]:
    """Compute SIMILAR_TO edges by querying Neo4j vector indexes.

    Args:
        store: Neo4j store used to issue vector index queries.
        embeddings: List of ``(id, code_embedding, description_embedding)`` tuples.
            Either embedding may be ``None``. Functions with neither are skipped.
        repo: Repository name used to filter results to the same repo.
        config: Similarity thresholds, weights, and top-N limit.
        include_tests: When ``True``, test functions are included as candidates.

    Returns:
        Deduplicated list of ``SimilarityEdge`` objects where
        ``source_id < target_id``.
    """
    if len(embeddings) < 2:
        return []

    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _query_one(
        func_id: str,
        code_vec: list[float] | None,
        desc_vec: list[float] | None,
    ) -> list[SimilarityEdge]:
        async with sem:
            async def _empty() -> list[tuple[str, float]]:
                return []

            code_coro = (
                store.query_code_neighbors(func_id, code_vec, repo, config.top_n, include_tests)
                if code_vec is not None
                else _empty()
            )
            desc_coro = (
                store.query_desc_neighbors(func_id, desc_vec, repo, config.top_n, include_tests)
                if desc_vec is not None
                else _empty()
            )
            code_results, desc_results = await asyncio.gather(code_coro, desc_coro)

        # Merge candidates from both indexes by target id.
        candidates: dict[str, dict[str, float]] = {}
        for b_id, score in code_results:
            candidates.setdefault(b_id, {"code_sim": 0.0, "desc_sim": 0.0})
            candidates[b_id]["code_sim"] = score
        for b_id, score in desc_results:
            candidates.setdefault(b_id, {"code_sim": 0.0, "desc_sim": 0.0})
            candidates[b_id]["desc_sim"] = score

        local_edges: list[SimilarityEdge] = []
        for b_id, sims in candidates.items():
            # Deduplicate: only create edge when source < target to avoid duplicates
            # when B's query later finds A.
            if func_id >= b_id:
                continue

            code_sim = sims["code_sim"]
            desc_sim = sims["desc_sim"]

            if code_sim > 0.0 and desc_sim > 0.0:
                combined = config.code_weight * code_sim + config.description_weight * desc_sim
            elif code_sim > 0.0:
                combined = code_sim
            else:
                combined = desc_sim

            if combined < config.threshold:
                continue

            local_edges.append(SimilarityEdge(
                source_id=func_id,
                target_id=b_id,
                code_similarity=code_sim,
                description_similarity=desc_sim,
                combined_similarity=combined,
            ))
        return local_edges

    tasks = [
        _query_one(func_id, code_vec, desc_vec)
        for func_id, code_vec, desc_vec in embeddings
        if code_vec is not None or desc_vec is not None
    ]
    results = await asyncio.gather(*tasks)

    edges: list[SimilarityEdge] = []
    for batch in results:
        edges.extend(batch)
    return edges
