"""Task dispatcher for the Slack-driven scheduler.

Replaces WorkflowExecutor. Routes SlackTask instances by type: QueryTask
runs a semantic search and posts results back to response_url; PipelineTask
runs the full embedding pipeline.
"""

from __future__ import annotations

import httpx

from src.pipeline.contracts import PipelineConfig
from src.scheduler.slack_task import PipelineTask, QueryTask, SlackTask

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
    """Routes SlackTask instances to the appropriate handler.

    Resources (OllamaClient, Neo4jStore, EmbeddingPipeline) are created and
    closed per-execution to match the lifecycle pattern used by EmbeddingPipeline
    itself. This avoids long-lived connection state in the dispatcher.
    """

    def __init__(self, pipeline_config: PipelineConfig) -> None:
        self._config = pipeline_config

    async def execute(self, task: SlackTask) -> None:
        if isinstance(task, QueryTask):
            await self._handle_query(task)
        elif isinstance(task, PipelineTask):
            await self._handle_pipeline(task)

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
            result = await search(store, client, task.query_text, task.repo, self._config, task.top_n)
            payload = _format_query_result(task.query_text, result.matches)
        except Exception as exc:
            payload = {"text": f"Search failed: {exc}"}
        finally:
            await client.close()
            await store.close()

        async with httpx.AsyncClient() as http:
            await http.post(task.response_url, json=payload)

    async def _handle_pipeline(self, task: PipelineTask) -> None:
        from src.pipeline.pipeline import EmbeddingPipeline

        pipeline = EmbeddingPipeline(self._config, skip_descriptions=task.no_descriptions)
        try:
            await pipeline.run()
        finally:
            await pipeline.close()
