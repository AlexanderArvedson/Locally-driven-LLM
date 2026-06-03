"""Embedding service for code and description vectors.

Wraps ``OllamaClient.embed()`` with batching and concurrency control so the
pipeline does not overwhelm the Ollama server.
"""

from __future__ import annotations

import asyncio
import json

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import FunctionRecord, PipelineConfig


class EmbeddingService:
    """Generates code and description embeddings using OllamaClient."""

    def __init__(self, client: OllamaClient, config: PipelineConfig) -> None:
        self._client = client
        self._model = config.embedding_model
        self._allow_gpu = config.allow_gpu

    async def embed_code(self, record: FunctionRecord) -> None:
        """Populate ``record.code_embedding`` in-place."""
        if not record.source_code.strip():
            return
        result = await self._client.embed(
            record.source_code,
            model=self._model,
            allow_gpu=self._allow_gpu,
        )
        record.code_embedding = result.embedding

    async def embed_description(self, record: FunctionRecord) -> None:
        """Populate ``record.description_embedding`` in-place.

        Extracts the ``summary`` field from the JSON description string and
        embeds it. Falls back to embedding the raw description if it is not
        valid JSON.
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

        result = await self._client.embed(
            text,
            model=self._model,
            allow_gpu=self._allow_gpu,
        )
        record.description_embedding = result.embedding

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
