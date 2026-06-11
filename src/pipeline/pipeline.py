"""Main pipeline orchestrator.

Runs the full extraction → embedding → description → storage → similarity
sequence as a linear async workflow. No LangGraph — a simple sequential
``run()`` method is sufficient because there is no branching.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from loguru import logger

from src.api.slack_notifier import SlackNotifier
from src.core.ollama_client import OllamaClient
from src.pipeline.checkpoint import CheckpointManager, make_run_key
from src.pipeline.contracts import PipelineConfig, PipelineResult
from src.pipeline.descriptions.service import DescriptionService
from src.pipeline.embeddings.service import EmbeddingService
from src.pipeline.extraction.extractor import FunctionExtractor
from src.pipeline.graph.store import Neo4jStore
from src.pipeline.graph.similarity import compute_similarity_edges


class EmbeddingPipeline:
    """Orchestrates all pipeline stages for a single repository."""

    def __init__(
        self,
        config: PipelineConfig,
        dry_run: bool = False,
        skip_descriptions: bool = False,
        notifier: SlackNotifier | None = None,
    ) -> None:
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
        self._notifier = notifier if notifier is not None else SlackNotifier(config.slack)

    async def close(self) -> None:
        await self._client.close()
        await self._store.close()

    async def run(self) -> PipelineResult:
        """Execute all pipeline stages and return a summary."""
        result = PipelineResult()
        start = time.monotonic()

        await self._notifier.pipeline_start(self._config.repo_name)
        try:
            await self._run_stages(result)
        except Exception as e:
            result.errors.append(str(e))
            logger.exception("Pipeline failed")
            await self._notifier.pipeline_failed(str(e))
        finally:
            result.duration_seconds = time.monotonic() - start
            if not result.errors:
                await self._notifier.pipeline_complete(result)

        return result

    def _sync_repo(self):
        """Ensure the target repo exists and is on the correct base branch before extraction.

        Returns a SyncResult if sync was attempted, or None if no repo_url is configured.
        """
        cfg = self._config
        if not cfg.repo_url:
            logger.debug("No repo_url configured — skipping repo sync.")
            return None
        sync_path = cfg.git_sync_path or cfg.repo_path
        from src.git.branch_manager import ensure_repo_synced
        return ensure_repo_synced(cfg.repo_url, sync_path, cfg.base_branch, cfg.git_username, cfg.git_token)

    async def _run_stages(self, result: PipelineResult) -> None:
        config = self._config

        # Repo sync
        await self._notifier.sync_start()
        sync_result = self._sync_repo()
        if sync_result is not None:
            await self._notifier.sync_complete(sync_result)

        # Stage 1: ensure Neo4j schema exists.
        if not self._dry_run:
            logger.info("Ensuring Neo4j schema...")
            await self._store.ensure_schema()

        # Stage 2: extract all functions from disk.
        logger.info("Extracting functions from {}...", config.repo_path)
        t_extract = time.monotonic()
        all_records = self._extractor.extract_all()
        extraction_duration = time.monotonic() - t_extract
        result.total_extracted = len(all_records)
        logger.info("Extracted {} functions", result.total_extracted)

        # Stage 2b: drop functions below the configured LOC threshold.
        threshold = config.limits.min_loc_threshold
        if threshold > 0:
            before = len(all_records)
            all_records = [r for r in all_records if (r.end_line - r.start_line + 1) >= threshold]
            result.loc_filtered = before - len(all_records)
            if result.loc_filtered:
                logger.info(
                    "Filtered {} functions below {} LOC threshold",
                    result.loc_filtered,
                    threshold,
                )

        files_processed = len({r.file_path for r in all_records})
        await self._notifier.extraction_complete(files_processed, result.total_extracted, extraction_duration)

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

        # Restore expensive fields from a previous run so we skip already-done work.
        _checkpoint = CheckpointManager(config.checkpoint)
        _run_key = make_run_key(changed) if changed else ""
        if changed and _run_key:
            _saved = _checkpoint.load(config.repo_name, _run_key)
            if _saved:
                for r in changed:
                    if r.id in _saved:
                        for field, val in _saved[r.id].items():
                            if val is not None:
                                setattr(r, field, val)
                restored = sum(1 for r in changed if r.description_status == "ok")
                logger.info("Checkpoint: {} descriptions already completed, skipping", restored)

        # Stages 5-7: embed and describe changed records.
        # Skipped entirely in dry-run — the extracted counts above are sufficient
        # to validate extraction without making expensive Ollama calls.
        if not self._dry_run and changed:
            needs_code_embed = [r for r in changed if r.code_embedding_status not in ("ok", "skipped", "chunked")]
            logger.info("Embedding source code for {} functions...", len(needs_code_embed))
            await self._notifier.embedding_start(len(needs_code_embed), "code")
            t_code_embed = time.monotonic()

            async def _on_code_progress(done: int, total: int) -> None:
                await self._notifier.progress("Code embedding", done, total, t_code_embed)

            await self._embedder.embed_code_batch(needs_code_embed, on_progress=_on_code_progress)
            code_failures = sum(1 for r in changed if r.code_embedding_status not in ("ok", "skipped", None))
            await self._notifier.embedding_complete(
                len(needs_code_embed) - code_failures, code_failures, time.monotonic() - t_code_embed, "code"
            )
            _checkpoint.save(config.repo_name, _run_key, changed)

            if not self._skip_descriptions:
                needs_description = [r for r in changed if r.description_status != "ok"]
                logger.info("Generating descriptions for {} functions...", len(needs_description))
                await self._notifier.description_start(len(needs_description))
                t_desc = time.monotonic()

                async def _on_desc_progress(done: int, total: int) -> None:
                    await self._notifier.progress("Description generation", done, total, t_desc)
                    if done > 0 and done % config.checkpoint.interval == 0:
                        _checkpoint.save(config.repo_name, _run_key, changed)

                await self._describer.describe_batch(needs_description, on_progress=_on_desc_progress)
                desc_ok = sum(1 for r in changed if r.description_status == "ok")
                desc_skipped = sum(1 for r in changed if r.description_status == "skipped")
                await self._notifier.description_complete(desc_ok, desc_skipped, time.monotonic() - t_desc)

                described = [r for r in changed if r.description]
                if described:
                    logger.info("Embedding descriptions for {} functions...", len(described))
                    await self._notifier.embedding_start(len(described), "description")
                    t_desc_embed = time.monotonic()

                    async def _on_desc_embed_progress(done: int, total: int) -> None:
                        await self._notifier.progress("Description embedding", done, total, t_desc_embed)

                    await self._embedder.embed_description_batch(described, on_progress=_on_desc_embed_progress)
                    desc_embed_failures = sum(1 for r in described if r.description_embedding is None)
                    await self._notifier.embedding_complete(
                        len(described) - desc_embed_failures,
                        desc_embed_failures,
                        time.monotonic() - t_desc_embed,
                        "description",
                    )
                    _checkpoint.save(config.repo_name, _run_key, changed)
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
            if _run_key:
                _checkpoint.clear(config.repo_name, _run_key)

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
        await self._notifier.similarity_start(len(embeddings))
        t_sim = time.monotonic()
        edges = await compute_similarity_edges(
            self._store, embeddings, config.repo_name, config.similarity,
            include_tests=config.include_tests_in_graph,
        )
        result.edges_written = len(edges)
        await self._notifier.similarity_complete(result.edges_written, time.monotonic() - t_sim)
        logger.info("Writing {} similarity edges...", result.edges_written)

        # Delete existing edges before re-inserting so stale edges from
        # functions whose embeddings changed do not survive the update.
        await self._store.delete_similarity_edges(config.repo_name)
        if edges:
            await self._store.upsert_similarity_edges_batch(edges)
