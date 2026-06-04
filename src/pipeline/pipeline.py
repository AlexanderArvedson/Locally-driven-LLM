"""Main pipeline orchestrator.

Runs the full extraction → embedding → description → storage → similarity
sequence as a linear async workflow. No LangGraph — a simple sequential
``run()`` method is sufficient because there is no branching.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from loguru import logger

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import PipelineConfig, PipelineResult
from src.pipeline.describer import DescriptionService
from src.pipeline.embedder import EmbeddingService
from src.pipeline.extractor import FunctionExtractor
from src.pipeline.neo4j_store import Neo4jStore
from src.pipeline.similarity import compute_similarity_edges


class EmbeddingPipeline:
    """Orchestrates all pipeline stages for a single repository."""

    def __init__(self, config: PipelineConfig, dry_run: bool = False, skip_descriptions: bool = False) -> None:
        self._config = config
        self._dry_run = dry_run
        self._skip_descriptions = skip_descriptions
        self._client = OllamaClient(base_url=config.embedding_url)
        self._store = Neo4jStore(
            config.neo4j,
            function_batch_size=config.batch_sizes.function_upsert,
            edge_batch_size=config.batch_sizes.edge_upsert,
        )
        self._extractor = FunctionExtractor(config)
        self._embedder = EmbeddingService(self._client, config)
        self._describer = DescriptionService(self._client, config)

    async def close(self) -> None:
        await self._client.close()
        await self._store.close()

    async def run(self) -> PipelineResult:
        """Execute all pipeline stages and return a summary."""
        result = PipelineResult()
        start = time.monotonic()

        try:
            await self._run_stages(result)
        except Exception as e:
            result.errors.append(str(e))
            logger.exception("Pipeline failed")
        finally:
            result.duration_seconds = time.monotonic() - start

        return result

    async def _run_stages(self, result: PipelineResult) -> None:
        config = self._config

        # Stage 1: ensure Neo4j schema exists.
        if not self._dry_run:
            logger.info("Ensuring Neo4j schema...")
            await self._store.ensure_schema()

        # Stage 2: extract all functions from disk.
        logger.info("Extracting functions from {}...", config.repo_path)
        all_records = self._extractor.extract_all()
        result.total_extracted = len(all_records)
        logger.info("Extracted {} functions", result.total_extracted)

        if not all_records:
            return

        # Stage 3: load existing source hashes to detect changes.
        # Runs even in dry_run so the change/unchanged counts are accurate.
        existing_hashes = await self._store.get_existing_hashes(config.repo_name)

        # Stage 4: partition into changed and unchanged records.
        changed = [r for r in all_records if existing_hashes.get(r.id) != r.source_hash]
        unchanged = [r for r in all_records if existing_hashes.get(r.id) == r.source_hash]
        result.changed = len(changed)
        result.unchanged = len(unchanged)
        logger.info("{} changed, {} unchanged", result.changed, result.unchanged)

        # Stages 5-7: embed and describe changed records.
        # Skipped entirely in dry-run — the extracted counts above are sufficient
        # to validate extraction without making expensive Ollama calls.
        if not self._dry_run and changed:
            logger.info("Embedding source code for {} functions...", len(changed))
            await self._embedder.embed_code_batch(changed)

            if not self._skip_descriptions:
                logger.info("Generating descriptions for {} functions...", len(changed))
                await self._describer.describe_batch(changed)

                described = [r for r in changed if r.description]
                if described:
                    logger.info("Embedding descriptions for {} functions...", len(described))
                    await self._embedder.embed_description_batch(described)
            else:
                logger.info("Skipping description generation (--no-descriptions)")
                for r in changed:
                    r.description_status = "skipped"

        # Update lastSeenAt for all records (including unchanged ones).
        now = datetime.now(timezone.utc).isoformat()
        for r in all_records:
            r.last_seen_at = now

        # Stage 8: upsert all records to Neo4j.
        if not self._dry_run:
            logger.info("Upserting {} function nodes...", len(all_records))
            await self._store.upsert_functions_batch(all_records)

        # Stage 9: soft-delete functions no longer in the repo.
        if not self._dry_run:
            seen_ids = {r.id for r in all_records}
            result.newly_deleted = await self._store.soft_delete_missing(config.repo_name, seen_ids)
            if result.newly_deleted:
                logger.info("Soft-deleted {} stale functions", result.newly_deleted)

        # Stage 10–12: similarity graph (skip if dry-run or fewer than 2 functions).
        if self._dry_run or result.total_extracted < 2:
            return

        logger.info("Loading embeddings for similarity computation...")
        embeddings = await self._store.get_all_embeddings(
            config.repo_name,
            include_tests=config.include_tests_in_graph,
        )
        if len(embeddings) < 2:
            return

        logger.info("Computing similarity edges for {} functions...", len(embeddings))
        edges = compute_similarity_edges(embeddings, config.similarity)
        result.edges_written = len(edges)
        logger.info("Writing {} similarity edges...", result.edges_written)

        # Delete existing edges before re-inserting so stale edges from
        # functions whose embeddings changed do not survive the update.
        await self._store.delete_similarity_edges(config.repo_name)
        if edges:
            await self._store.upsert_similarity_edges_batch(edges)
