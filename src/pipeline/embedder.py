"""Embedding service for code and description vectors.

Wraps ``OllamaClient.embed()`` with batching and concurrency control so the
pipeline does not overwhelm the Ollama server.
"""

from __future__ import annotations

import asyncio
import json

from loguru import logger

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import FunctionRecord, PipelineConfig

# nomic-embed-text supports 8192 tokens. We explicitly request that context
# in the embed call. At ~3-4 chars/token for code, 24 000 chars ≈ 6 000-8 000
# tokens — leave a ~10% safety margin by capping at 22 000 chars.
_MAX_CODE_CHARS = 22_000


class EmbeddingService:
    """Generates code and description embeddings using OllamaClient."""

    def __init__(self, client: OllamaClient, config: PipelineConfig) -> None:
        self._client = client
        self._model = config.embedding_model
        self._allow_gpu = config.allow_gpu

    async def embed_code(self, record: FunctionRecord) -> None:
        """Populate ``record.code_embedding`` in-place.

        Logs and skips on failure so a single bad function does not abort
        the batch.
        """
        text = record.source_code.strip()
        if not text:
            return
        try:
            result = await self._client.embed(
                text[:_MAX_CODE_CHARS],
                model=self._model,
                allow_gpu=self._allow_gpu,
            )
            record.code_embedding = result.embedding
        except Exception as e:
            logger.warning(
                "Skipping code embedding for {} ({}): {}",
                record.qualified_name,
                record.file_path,
                e,
            )

    async def embed_description(self, record: FunctionRecord) -> None:
        """Populate ``record.description_embedding`` in-place.

        Extracts the ``summary`` field from the JSON description string and
        embeds it. Logs and skips on failure.
        """
        if not record.description:
            return

        text = record.description
        try:
            parsed = json.loads(record.description)
            text = parsed.get("summary", record.description)
        except (json.JSONDecodeError, AttributeError):
            pass

        if not text.strip():
            return

        try:
            result = await self._client.embed(
                text,
                model=self._model,
                allow_gpu=self._allow_gpu,
            )
            record.description_embedding = result.embedding
        except Exception as e:
            logger.warning(
                "Skipping description embedding for {} ({}): {}",
                record.qualified_name,
                record.file_path,
                e,
            )

    async def embed_code_batch(
        self,
        records: list[FunctionRecord],
        concurrency: int = 4,
    ) -> None:
        """Embed source code for all records in-place, respecting concurrency limit."""
        sem = asyncio.Semaphore(concurrency)

        async def _embed_one(record: FunctionRecord) -> None:
            async with sem:
                await self.embed_code(record)

        await asyncio.gather(*[_embed_one(r) for r in records])

    async def embed_description_batch(
        self,
        records: list[FunctionRecord],
        concurrency: int = 4,
    ) -> None:
        """Embed descriptions for all records in-place, respecting concurrency limit."""
        sem = asyncio.Semaphore(concurrency)

        async def _embed_one(record: FunctionRecord) -> None:
            async with sem:
                await self.embed_description(record)

        await asyncio.gather(*[_embed_one(r) for r in records])
