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

_SHOW_VECTOR_INDEXES: LiteralString = "SHOW INDEXES WHERE type = 'VECTOR'"

_INDEX_NAMES = frozenset({"function_code_embedding_index", "function_desc_embedding_index"})

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
  f.description           = CASE WHEN rec.description IS NOT NULL THEN rec.description ELSE f.description END,
  f.codeEmbedding         = CASE WHEN rec.codeEmbedding        IS NOT NULL THEN rec.codeEmbedding        ELSE f.codeEmbedding        END,
  f.descriptionEmbedding  = CASE WHEN rec.descriptionEmbedding IS NOT NULL THEN rec.descriptionEmbedding ELSE f.descriptionEmbedding END,
  f.updatedAt             = rec.updatedAt,
  f.lastSeenAt            = rec.lastSeenAt,
  f.isTest                = rec.isTest,
  f.isAnonymous           = rec.isAnonymous,
  f.createdAt             = CASE WHEN f.createdAt IS NULL THEN rec.createdAt ELSE f.createdAt END,
  f.codeEmbeddingStatus        = CASE WHEN rec.codeEmbeddingStatus IS NOT NULL        THEN rec.codeEmbeddingStatus        ELSE f.codeEmbeddingStatus        END,
  f.codeEmbeddingInputChars    = CASE WHEN rec.codeEmbeddingInputChars IS NOT NULL    THEN rec.codeEmbeddingInputChars    ELSE f.codeEmbeddingInputChars    END,
  f.codeEmbeddingTruncatedChars= CASE WHEN rec.codeEmbeddingTruncatedChars IS NOT NULL THEN rec.codeEmbeddingTruncatedChars ELSE f.codeEmbeddingTruncatedChars END,
  f.descriptionStatus          = CASE WHEN rec.descriptionStatus IS NOT NULL          THEN rec.descriptionStatus          ELSE f.descriptionStatus          END
"""

_GET_HASHES: LiteralString = """
MATCH (f:Function {repo: $repo})
RETURN f.id AS id, f.sourceHash AS sourceHash
"""

_COUNT_MISSING: LiteralString = """
MATCH (f:Function {repo: $repo})
WHERE NOT f.id IN $seen_ids
RETURN count(f) AS deleted
"""

_HARD_DELETE: LiteralString = """
MATCH (f:Function {repo: $repo})
WHERE NOT f.id IN $seen_ids
DETACH DELETE f
"""

_DELETE_SIMILARITY_EDGES: LiteralString = """
MATCH (f:Function {repo: $repo})-[r:SIMILAR_TO]->()
DELETE r
"""

_GET_ALL_EMBEDDINGS: LiteralString = """
MATCH (f:Function {repo: $repo})
WHERE (f.isTest = false OR $include_tests)
  AND f.isAnonymous = false
  AND (f.codeEmbedding IS NOT NULL OR f.descriptionEmbedding IS NOT NULL)
RETURN f.id AS id, f.codeEmbedding AS codeEmbedding, f.descriptionEmbedding AS descriptionEmbedding
"""

_QUERY_CODE_NEIGHBORS: LiteralString = """
CALL db.index.vector.queryNodes('function_code_embedding_index', $top_n, $embedding)
YIELD node AS b, score
WHERE b.id <> $source_id
  AND b.repo = $repo
  AND b.isAnonymous = false
  AND (b.isTest = false OR $include_tests)
RETURN b.id AS id, score
"""

_QUERY_DESC_NEIGHBORS: LiteralString = """
CALL db.index.vector.queryNodes('function_desc_embedding_index', $top_n, $embedding)
YIELD node AS b, score
WHERE b.id <> $source_id
  AND b.repo = $repo
  AND b.isAnonymous = false
  AND (b.isTest = false OR $include_tests)
RETURN b.id AS id, score
"""

_GET_FUNCTIONS_BY_IDS: LiteralString = """
MATCH (f:Function)
WHERE f.id IN $ids
RETURN f.id AS id, f.qualifiedName AS qualifiedName,
       f.filePath AS filePath, f.description AS description
"""

_UPSERT_EDGE: LiteralString = """
UNWIND $edges AS edge
MATCH (a:Function {id: edge.sourceId})
MATCH (b:Function {id: edge.targetId})
MERGE (a)-[r:SIMILAR_TO]->(b)
ON CREATE SET
  r.createdAt             = edge.createdAt
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

    def __init__(
        self,
        config: Neo4jConfig,
        function_batch_size: int = 50,
        edge_batch_size: int = 200,
    ) -> None:
        self._config = config
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password),
        )
        self._vector_dim: int | None = None
        self._function_batch_size = function_batch_size
        self._edge_batch_size = edge_batch_size

    @property
    def database_name(self) -> str:
        """The configured Neo4j database name."""
        return self._config.database

    async def close(self) -> None:
        """Close the driver connection pool."""
        await self._driver.close()

    async def run_query(self, query: LiteralString, **params) -> list[dict]:
        """Execute a read Cypher query and return all result rows as dicts."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(query, **params)
            return await result.data()

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
        """Create vector indexes once the embedding dimension is known.

        Raises RuntimeError if an existing index was built with a different
        dimension — which happens when the embedding model is changed after the
        first run. Drop both indexes in Neo4j Browser before switching models:
            DROP INDEX function_code_embedding_index
            DROP INDEX function_desc_embedding_index
        """
        if self._vector_dim == dim:
            return
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_SHOW_VECTOR_INDEXES)
            existing = await result.data()
            for idx in existing:
                if idx.get("name") not in _INDEX_NAMES:
                    continue
                existing_dim = (
                    (idx.get("options") or {})
                    .get("indexConfig", {})
                    .get("vector.dimensions")
                )
                if existing_dim is not None and existing_dim != dim:
                    raise RuntimeError(
                        f"Vector index '{idx['name']}' has dimension {existing_dim} but the "
                        f"current embedding model produces {dim}-dimensional vectors. "
                        f"Drop both indexes in Neo4j Browser before switching models:\n"
                        f"  DROP INDEX function_code_embedding_index\n"
                        f"  DROP INDEX function_desc_embedding_index"
                    )
            self._vector_dim = dim
            await session.run(_ddl(_VECTOR_INDEX_CODE, dim=dim))
            await session.run(_ddl(_VECTOR_INDEX_DESC, dim=dim))

    async def get_existing_hashes(self, repo: str) -> dict[str, str]:
        """Return ``{function_id: source_hash}`` for all live functions in the repo."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_GET_HASHES, repo=repo)
            records = await result.data()
        return {r["id"]: r["sourceHash"] for r in records}

    async def upsert_functions_batch(self, records: list[FunctionRecord]) -> None:
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
                "isTest": r.is_test,
                "isAnonymous": r.is_anonymous,
                "codeEmbeddingStatus": r.code_embedding_status,
                "codeEmbeddingInputChars": r.code_embedding_input_chars,
                "codeEmbeddingTruncatedChars": r.code_embedding_truncated_chars,
                "descriptionStatus": r.description_status,
            }

        async with self._driver.session(database=self._config.database) as session:
            for i in range(0, len(records), self._function_batch_size):
                batch = [_to_dict(r) for r in records[i:i + self._function_batch_size]]
                await session.run(_UPSERT_FUNCTION, records=batch)

    async def delete_missing(self, repo: str, seen_ids: set[str]) -> int:
        """Permanently delete functions not in ``seen_ids``. Returns count deleted."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_COUNT_MISSING, repo=repo, seen_ids=list(seen_ids))
            record = await result.single()
            count = record["deleted"] if record else 0
            if count:
                await session.run(_HARD_DELETE, repo=repo, seen_ids=list(seen_ids))
        return count

    async def get_all_embeddings(
        self,
        repo: str,
        include_tests: bool = False,
    ) -> list[tuple[str, list[float] | None, list[float] | None]]:
        """Return ``[(id, code_embedding, description_embedding)]`` for all live functions.

        Args:
            include_tests: When ``True``, test functions (``isTest = true``) are
                included in the returned set and therefore in the similarity graph.
        """
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_GET_ALL_EMBEDDINGS, repo=repo, include_tests=include_tests)
            records = await result.data()
        return [(r["id"], r["codeEmbedding"], r["descriptionEmbedding"]) for r in records]

    async def query_code_neighbors(
        self,
        source_id: str,
        embedding: list[float],
        repo: str,
        top_n: int,
        include_tests: bool = False,
    ) -> list[tuple[str, float]]:
        """Return top-N code-similar functions using the HNSW vector index.

        Results are ordered by cosine similarity descending (as returned by Neo4j).
        Only live functions in ``repo`` are returned; ``source_id`` is excluded.
        """
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(
                _QUERY_CODE_NEIGHBORS,
                source_id=source_id,
                embedding=embedding,
                repo=repo,
                top_n=top_n,
                include_tests=include_tests,
            )
            records = await result.data()
        return [(r["id"], r["score"]) for r in records]

    async def query_desc_neighbors(
        self,
        source_id: str,
        embedding: list[float],
        repo: str,
        top_n: int,
        include_tests: bool = False,
    ) -> list[tuple[str, float]]:
        """Return top-N description-similar functions using the HNSW vector index.

        Same contract as :meth:`query_code_neighbors` but queries the description
        embedding index.
        """
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(
                _QUERY_DESC_NEIGHBORS,
                source_id=source_id,
                embedding=embedding,
                repo=repo,
                top_n=top_n,
                include_tests=include_tests,
            )
            records = await result.data()
        return [(r["id"], r["score"]) for r in records]

    async def delete_similarity_edges(self, repo: str) -> None:
        """Delete all SIMILAR_TO edges originating from functions in this repo.

        Called before re-inserting the similarity graph so stale edges from
        functions whose embeddings changed do not persist.
        """
        async with self._driver.session(database=self._config.database) as session:
            await session.run(_DELETE_SIMILARITY_EDGES, repo=repo)

    async def get_functions_by_ids(self, ids: list[str]) -> list[dict]:
        """Return qualifiedName, filePath, and description for each requested function id."""
        async with self._driver.session(database=self._config.database) as session:
            result = await session.run(_GET_FUNCTIONS_BY_IDS, ids=ids)
            return await result.data()

    async def upsert_similarity_edges_batch(self, edges: list[SimilarityEdge]) -> None:
        """Batch-upsert SIMILAR_TO relationships using UNWIND."""
        def _to_dict(e: SimilarityEdge) -> dict:
            return {
                "sourceId": e.source_id,
                "targetId": e.target_id,
                "codeSimilarity": e.code_similarity,
                "descriptionSimilarity": e.description_similarity,
                "combinedSimilarity": e.combined_similarity,
                "createdAt": e.created_at,
                "updatedAt": e.updated_at,
            }

        async with self._driver.session(database=self._config.database) as session:
            for i in range(0, len(edges), self._edge_batch_size):
                batch = [_to_dict(e) for e in edges[i:i + self._edge_batch_size]]
                await session.run(_UPSERT_EDGE, edges=batch)
