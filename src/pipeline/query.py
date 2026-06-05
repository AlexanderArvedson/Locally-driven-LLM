"""Semantic search engine for functions stored in Neo4j.

Embeds a free-text query with the same model used by the pipeline and
retrieves the closest matching functions via the HNSW vector indexes.
No dependency on the scheduler, FastAPI, or Slack.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import PipelineConfig
from src.pipeline.neo4j_store import Neo4jStore


@dataclass
class QueryMatch:
    """A single function returned by a semantic search."""

    function_name: str
    qualified_name: str
    file_path: str
    score: float
    description: str | None


@dataclass
class QueryResult:
    """Aggregated result from a semantic search over the Neo4j vector indexes."""

    query: str
    matches: list[QueryMatch]
    index_used: str  # "code", "description", or "both"


async def search(
    store: Neo4jStore,
    client: OllamaClient,
    query_text: str,
    repo: str,
    config: PipelineConfig,
    top_n: int = 10,
) -> QueryResult:
    """Embed query_text and return the top-N most similar functions from Neo4j.

    Queries both the code and description HNSW indexes concurrently, merges
    the results by taking the highest score for each function id, and fetches
    function metadata for the final ranked list.
    """
    embed_result = await client.embed(
        query_text,
        model=config.embedding_model,
        allow_gpu=config.allow_gpu,
        num_ctx=config.limits.embedding_num_ctx,
    )
    vec = embed_result.embedding

    # Query both indexes concurrently using a sentinel source_id that won't
    # match any stored function, so the exclusion filter has no effect.
    code_hits, desc_hits = await asyncio.gather(
        store.query_code_neighbors(
            source_id="__query__",
            embedding=vec,
            repo=repo,
            top_n=top_n,
        ),
        store.query_desc_neighbors(
            source_id="__query__",
            embedding=vec,
            repo=repo,
            top_n=top_n,
        ),
    )

    # Merge by id, keeping the highest score from either index.
    scores: dict[str, float] = {}
    for fid, score in (*code_hits, *desc_hits):
        if score > scores.get(fid, 0.0):
            scores[fid] = score

    ranked_ids = sorted(scores, key=lambda fid: scores[fid], reverse=True)[:top_n]

    if not ranked_ids:
        return QueryResult(query=query_text, matches=[], index_used="both")

    rows = await store.get_functions_by_ids(ranked_ids)
    by_id = {r["id"]: r for r in rows}

    matches: list[QueryMatch] = []
    for fid in ranked_ids:
        row = by_id.get(fid)
        if row is None:
            continue
        qualified = row["qualifiedName"] or fid
        # Extract the bare function name from the qualified name (last segment).
        function_name = qualified.rsplit(".", 1)[-1]
        matches.append(
            QueryMatch(
                function_name=function_name,
                qualified_name=qualified,
                file_path=row["filePath"] or "",
                score=scores[fid],
                description=row.get("description"),
            )
        )

    return QueryResult(query=query_text, matches=matches, index_used="both")
