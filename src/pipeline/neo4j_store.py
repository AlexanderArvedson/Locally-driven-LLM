"""Neo4j data store for Function nodes and SIMILAR_TO relationships.

Uses the official async neo4j Python driver. All session management is
internal; callers work entirely with FunctionRecord and SimilarityEdge
dataclasses.

Vector index dimensions are inferred lazily from the first embedding written,
so ``ensure_schema`` must be called once before any upsert operations.
"""

from __future__ import annotations

from typing import LiteralString, cast

from neo4j import AsyncDriver, AsyncGraphDatabase

from src.pipeline.contracts import FunctionRecord, Neo4jConfig, SimilarityEdge


def _ddl(template: str, **kwargs: int) -> LiteralString:
    """Format a DDL template with integer-only substitutions and assert LiteralString.

    Neo4j DDL statements (CREATE VECTOR INDEX) cannot use query parameters for
    values like dimension counts, so string formatting is unavoidable. The cast
    is safe because the template is a module-level constant and all substituted
    values are integers.
    """
    return cast(LiteralString, template.format(**kwargs))

# ---------------------------------------------------------------------------
# Cypher statements
# ---------------------------------------------------------------------------

_CONSTRAINT: LiteralString = """
CREATE CONSTRAINT function_id_unique IF NOT EXISTS
FOR (f:Function) REQUIRE f.id IS UNIQUE
"""

_INDEX_REPO = "CREATE INDEX function_repo_index IF NOT EXISTS FOR (f:Function) ON (f.repo)"
_INDEX_FILE = "CREATE INDEX function_file_path_index IF NOT EXISTS FOR (f:Function) ON (f.filePath)"
_INDEX_NAME = "CREATE INDEX function_name_index IF NOT EXISTS FOR (f:Function) ON (f.functionName)"

_VECTOR_INDEX_CODE: LiteralString = """
CREATE VECTOR INDEX function_code_embedding_index IF NOT EXISTS
FOR (f:Function) ON (f.codeEmbedding)
OPTIONS {{ indexConfig: {{ `vector.dimensions`: {dim}, `vector.similarity_function`: 'cosine' }} }}
"""

_VECTOR_INDEX_DESC: LiteralString = """
CREATE VECTOR INDEX function_desc_embedding_index IF NOT EXISTS
FOR (f:Function) ON (f.descriptionEmbedding)
OPTIONS {{ indexConfig: {{ `vector.dimensions`: {dim}, `vector.similarity_function`: 'cosine' }} }}
"""

_UPSERT_FUNCTION: LiteralString = """
UNWIND $records AS rec
MERGE (f:Function {id: rec.id})
SET
  f.repo                  = rec.repo,
  f.language              = rec.language,
  f.filePath              = rec.filePath,
  f.functionName          = rec.functionName,
  f.qualifiedName         = rec.qualifiedName,
  f.className             = rec.className,
  f.startLine             = rec.startLine,
  f.endLine               = rec.endLine,
  f.sourceCode            = rec.sourceCode,
  f.sourceHash            = rec.sourceHash,
  f.description           = rec.description,
  f.codeEmbedding         = rec.codeEmbedding,
  f.descriptionEmbedding  = rec.descriptionEmbedding,
  f.updatedAt             = rec.updatedAt,
  f.lastSeenAt            = rec.lastSeenAt,
  f.isDeleted             = false,
  f.createdAt             = CASE WHEN f.createdAt IS NULL THEN rec.createdAt ELSE f.createdAt END
"""

_GET_HASHES: LiteralString = """
MATCH (f:Function {repo: $repo})
WHERE f.isDeleted = false
RETURN f.id AS id, f.sourceHash AS sourceHash
"""

_SOFT_DELETE: LiteralString = """
MATCH (f:Function {repo: $repo})
WHERE NOT f.id IN $seen_ids AND f.isDeleted = false
SET f.isDeleted = true
RETURN count(f) AS deleted
"""

_GET_ALL_EMBEDDINGS: LiteralString = """
MATCH (f:Function {repo: $repo})
WHERE f.isDeleted = false AND f.codeEmbedding IS NOT NULL
RETURN f.id AS id, f.codeEmbedding AS codeEmbedding, f.descriptionEmbedding AS descriptionEmbedding
"""

_UPSERT_EDGE: LiteralString = """
UNWIND $edges AS edge
MATCH (a:Function {id: edge.sourceId})
MATCH (b:Function {id: edge.targetId})
MERGE (a)-[r:SIMILAR_TO]->(b)
SET
  r.codeSimilarity        = edge.codeSimilarity,
  r.descriptionSimilarity = edge.descriptionSimilarity,
  r.combinedSimilarity    = edge.combinedSimilarity,
  r.updatedAt             = edge.updatedAt
"""


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class Neo4jStore:
    """Async Neo4j driver wrapper for Function nodes and SIMILAR_TO edges."""

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password),
        )
        self._vector_dim: int | None = None

    async def close(self) -> None:
        """Close the driver connection pool."""
        await self._driver.close()

    async def ensure_schema(self, vector_dim: int | None = None) -> None:
        """Idempotently create constraints and indexes.

        Args:
            vector_dim: Embedding dimension for the vector indexes. When
                ``None``, vector indexes are skipped until the first upsert
                provides the dimension.
        """
        async with self._driver.session(database=self._config.database) as session:
            await session.run(_CONSTRAINT)
            await session.run(_INDEX_REPO)
            await session.run(_INDEX_FILE)
            await session.run(_INDEX_NAME)
            if vector_dim is not None:
                self._vector_dim = vector_dim
                await session.run(_ddl(_VECTOR_INDEX_CODE, dim=vector_dim))
                await session.run(_ddl(_VECTOR_INDEX_DESC, dim=vector_dim))

    async def _ensure_vector_indexes(self, dim: int) -> None:
        """Create vector indexes once the embedding dimension is known."""
        if self._vector_dim == dim:
            return
        self._vector_dim = dim
        async with self._driver.session(database=self._config.database) as session:
            await session.run(_ddl(_VECTOR_INDEX_CODE, dim=dim))
            await session.run(_ddl(_VECTOR_INDEX_DESC, dim=dim))

    async def get_existing_hashes(self, repo: str) -> dict[str, str]:
        """Return ``{function_id: source_hash}`` for all live functions in the repo."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_GET_HASHES, repo=repo)
            records = await result.data()
        return {r["id"]: r["sourceHash"] for r in records}

    async def upsert_functions_batch(
        self,
        records: list[FunctionRecord],
        batch_size: int = 50,
    ) -> None:
        """Batch-upsert Function nodes using UNWIND for efficiency."""
        # Infer and create vector indexes from the first embedding encountered.
        if self._vector_dim is None:
            for r in records:
                if r.code_embedding:
                    await self._ensure_vector_indexes(len(r.code_embedding))
                    break

        def _to_dict(r: FunctionRecord) -> dict:
            return {
                "id": r.id,
                "repo": r.repo,
                "language": r.language,
                "filePath": r.file_path,
                "functionName": r.function_name,
                "qualifiedName": r.qualified_name,
                "className": r.class_name,
                "startLine": r.start_line,
                "endLine": r.end_line,
                "sourceCode": r.source_code,
                "sourceHash": r.source_hash,
                "description": r.description,
                "codeEmbedding": r.code_embedding,
                "descriptionEmbedding": r.description_embedding,
                "createdAt": r.created_at,
                "updatedAt": r.updated_at,
                "lastSeenAt": r.last_seen_at,
            }

        async with self._driver.session(database=self._config.database) as session:
            for i in range(0, len(records), batch_size):
                batch = [_to_dict(r) for r in records[i:i + batch_size]]
                await session.run(_UPSERT_FUNCTION, records=batch)

    async def soft_delete_missing(self, repo: str, seen_ids: set[str]) -> int:
        """Mark functions not in ``seen_ids`` as deleted. Returns count."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_SOFT_DELETE, repo=repo, seen_ids=list(seen_ids))
            record = await result.single()
        return record["deleted"] if record else 0

    async def get_all_embeddings(
        self,
        repo: str,
    ) -> list[tuple[str, list[float], list[float] | None]]:
        """Return ``[(id, code_embedding, description_embedding)]`` for all live functions."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_GET_ALL_EMBEDDINGS, repo=repo)
            records = await result.data()
        return [(r["id"], r["codeEmbedding"], r["descriptionEmbedding"]) for r in records]

    async def upsert_similarity_edges_batch(
        self,
        edges: list[SimilarityEdge],
        batch_size: int = 200,
    ) -> None:
        """Batch-upsert SIMILAR_TO relationships using UNWIND."""
        def _to_dict(e: SimilarityEdge) -> dict:
            return {
                "sourceId": e.source_id,
                "targetId": e.target_id,
                "codeSimilarity": e.code_similarity,
                "descriptionSimilarity": e.description_similarity,
                "combinedSimilarity": e.combined_similarity,
                "updatedAt": e.updated_at,
            }

        async with self._driver.session(database=self._config.database) as session:
            for i in range(0, len(edges), batch_size):
                batch = [_to_dict(e) for e in edges[i:i + batch_size]]
                await session.run(_UPSERT_EDGE, edges=batch)
