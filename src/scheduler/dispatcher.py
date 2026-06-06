"""Task dispatcher for the Slack-driven scheduler.

Replaces WorkflowExecutor. Routes Task instances by type: QueryTask
runs a semantic search and posts results back to response_url; PipelineTask
runs the full embedding pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import replace

import httpx
from loguru import logger

from src.pipeline.contracts import PipelineConfig
from src.scheduler.task import PipelineTask, QueryTask, ReportTask, Task

_TOP_N_DISPLAY = 5


def _format_query_result(query_text: str, matches: list) -> dict:
    """Build a Slack mrkdwn text payload for a list of QueryMatch results."""
    if not matches:
        return {"text": f"No results found for: _{query_text}_"}

    lines = [f'*Results for:* "{query_text}"\n']
    for m in matches[:_TOP_N_DISPLAY]:
        lines.append(f"• `{m.qualified_name}`  ·  score {m.score:.2f}  ·  {m.file_path}")

    return {"response_type": "in_channel", "text": "\n".join(lines)}


class TaskDispatcher:
    """Routes Task instances to the appropriate handler.

    Resources (OllamaClient, Neo4jStore, EmbeddingPipeline) are created and
    closed per-execution to match the lifecycle pattern used by EmbeddingPipeline
    itself. This avoids long-lived connection state in the dispatcher.
    """

    def __init__(self, pipeline_config: PipelineConfig) -> None:
        self._config = pipeline_config

    async def execute(self, task: Task) -> None:
        if isinstance(task, QueryTask):
            await self._handle_query(task)
        elif isinstance(task, PipelineTask):
            await self._handle_pipeline(task)
        elif isinstance(task, ReportTask):
            await self._handle_report(task)

    async def _handle_query(self, task: QueryTask) -> None:
        from src.core.ollama_client import OllamaClient
        from src.pipeline.neo4j_store import Neo4jStore
        from src.pipeline.query import search

        client = OllamaClient(base_url=self._config.embedding_url)
        store = Neo4jStore(
            self._config.neo4j,
            function_batch_size=self._config.batch_sizes.function_upsert,
            edge_batch_size=self._config.batch_sizes.edge_upsert,
        )
        try:
            logger.info("[dispatcher] searching: {!r}", task.query_text)
            result = await search(store, client, task.query_text, task.repo, self._config, task.top_n)
            logger.info("[dispatcher] got {} matches", len(result.matches))
            payload = _format_query_result(task.query_text, result.matches)
        except Exception as exc:
            logger.exception("[dispatcher] search failed: {}", exc)
            payload = {"text": f"Search failed: {exc}"}
        finally:
            await client.close()
            await store.close()

        logger.info("[dispatcher] posting to response_url")
        async with httpx.AsyncClient() as http:
            await http.post(task.response_url, json=payload)
        logger.info("[dispatcher] done")

    async def _handle_pipeline(self, task: PipelineTask) -> None:
        from src.api.slack_notifier import notify_pipeline_result
        from src.pipeline.pipeline import EmbeddingPipeline

        config = replace(self._config, repo_name=task.repo)
        if task.path:
            config = replace(config, repo_path=task.path)
        logger.info("[dispatcher] pipeline starting — repo_path={} repo_name={} languages={}",
                    config.repo_path, config.repo_name, config.supported_languages)

        pipeline = EmbeddingPipeline(config, dry_run=task.dry_run, skip_descriptions=task.no_descriptions)
        try:
            result = await pipeline.run()
        finally:
            await pipeline.close()

        error = result.errors[0] if result.errors else None
        await notify_pipeline_result(not result.errors, result, error)

        if not task.no_report and not task.dry_run:
            await self._handle_report(ReportTask(
                id=str(uuid.uuid4()),
                repo=task.repo,
                loc_filtered=result.loc_filtered,
            ))

    async def _handle_report(self, task: ReportTask) -> None:
        import datetime

        from src.api.slack_notifier import notify_report_result
        from src.pipeline.reporter import generate_report

        config = replace(self._config, repo_name=task.repo)
        started_at = datetime.datetime.now()
        try:
            report_path = await generate_report(
                config.neo4j, config.repo_name,
                include_tests=config.include_tests_in_graph,
                pipeline_config=config,
                loc_filtered=task.loc_filtered,
            )
        except Exception as exc:
            await notify_report_result(False, started_at, None, str(exc))
            raise
        await notify_report_result(True, started_at, report_path, None)
