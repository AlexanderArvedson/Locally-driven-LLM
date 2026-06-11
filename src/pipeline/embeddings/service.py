"""Embedding service for code and description vectors.

Wraps ``OllamaClient.embed()`` with batching and concurrency control so the
pipeline does not overwhelm the Ollama server.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from loguru import logger

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import FunctionRecord, PipelineConfig

_CHUNK_SIZE_CHARS = 6_000
_CHUNK_OVERLAP_CHARS = 600


class EmbeddingService:
    """Generates code and description embeddings using OllamaClient."""

    def __init__(self, client: OllamaClient, config: PipelineConfig) -> None:
        self._client = client
        self._model = config.embedding_model
        self._allow_gpu = config.allow_gpu
        self._max_code_chars = config.limits.max_code_chars
        self._num_ctx = config.embedding_num_ctx
        self._context_overflow_threshold = config.limits.context_overflow_char_threshold
        self._embed_code_concurrency = config.concurrency.embed_code
        self._embed_description_concurrency = config.concurrency.embed_description

    def _chunk_source(self, text: str) -> list[str]:
        """Split text into overlapping windows of _CHUNK_SIZE_CHARS with _CHUNK_OVERLAP_CHARS overlap."""
        step = _CHUNK_SIZE_CHARS - _CHUNK_OVERLAP_CHARS
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + _CHUNK_SIZE_CHARS])
            start += step
        return chunks

    async def _embed_chunked(self, text: str) -> list[float]:
        """Embed text by splitting into chunks and returning the element-wise mean embedding."""
        chunks = self._chunk_source(text)
        results = await asyncio.gather(*[
            self._client.embed(chunk, model=self._model, allow_gpu=self._allow_gpu, num_ctx=self._num_ctx)
            for chunk in chunks
        ])
        vecs = [r.embedding for r in results]
        dim = len(vecs[0])
        return [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]

    async def embed_code(self, record: FunctionRecord) -> None:
        """Populate ``record.code_embedding`` and ``record.code_embedding_status`` in-place.

        Logs and skips on failure so a single bad function does not abort the batch.
        On failure, also stores ``code_embedding_input_chars`` and
        ``code_embedding_truncated_chars`` to help diagnose the failure.
        """
        text = record.source_code.strip()
        if not text:
            record.code_embedding_status = "skipped"
            return

        truncated = text  # overwritten in the non-chunked path; kept as fallback for diagnostics
        try:
            if len(text) >= self._context_overflow_threshold:
                record.code_embedding = await self._embed_chunked(text)
                record.code_embedding_status = "chunked"
            else:
                truncated = text[:self._max_code_chars]
                result = await self._client.embed(
                    truncated,
                    model=self._model,
                    allow_gpu=self._allow_gpu,
                    num_ctx=self._num_ctx,
                )
                record.code_embedding = result.embedding
                record.code_embedding_status = "ok"
        except asyncio.TimeoutError as e:
            record.code_embedding_status = "timeout"
            record.code_embedding_input_chars = len(text)
            record.code_embedding_truncated_chars = len(truncated)
            logger.warning(
                "Timeout embedding code for {} ({}): {}",
                record.qualified_name, record.file_path, e,
            )
        except RuntimeError as e:
            # RuntimeError is raised by OllamaClient for HTTP errors (including 500).
            record.code_embedding_status = "error"
            record.code_embedding_input_chars = len(text)
            record.code_embedding_truncated_chars = len(truncated)
            logger.warning(
                "Skipping code embedding for {} ({}): {}",
                record.qualified_name, record.file_path, e,
            )
        except Exception as e:
            record.code_embedding_status = "error"
            record.code_embedding_input_chars = len(text)
            record.code_embedding_truncated_chars = len(truncated)
            logger.warning(
                "Skipping code embedding for {} ({}): {}",
                record.qualified_name, record.file_path, e,
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
        on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        """Embed source code for all records in-place, respecting concurrency limit."""
        sem = asyncio.Semaphore(self._embed_code_concurrency)
        completed = 0

        async def _embed_one(record: FunctionRecord) -> None:
            nonlocal completed
            async with sem:
                await self.embed_code(record)
                completed += 1
                if on_progress is not None:
                    await on_progress(completed, len(records))

        await asyncio.gather(*[_embed_one(r) for r in records])

    async def embed_description_batch(
        self,
        records: list[FunctionRecord],
        on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        """Embed descriptions for all records in-place, respecting concurrency limit."""
        sem = asyncio.Semaphore(self._embed_description_concurrency)
        completed = 0

        async def _embed_one(record: FunctionRecord) -> None:
            nonlocal completed
            async with sem:
                await self.embed_description(record)
                completed += 1
                if on_progress is not None:
                    await on_progress(completed, len(records))

        await asyncio.gather(*[_embed_one(r) for r in records])
