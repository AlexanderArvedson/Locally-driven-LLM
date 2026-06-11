"""Description service for LLM-generated function summaries.

Wraps ``OllamaClient.chat()`` to produce structured JSON descriptions of
extracted functions. Retries once on invalid JSON before giving up.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable

from loguru import logger

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import FunctionRecord, PipelineConfig
from src.pipeline.descriptions.prompts import _PROMPT_TEMPLATE


def _extract_json(text: str) -> str:
    """Strip code fences and extract the outermost JSON object from the response.

    Handles models that emit prose before or after the JSON object despite
    being instructed not to (e.g. "Here is the description: {...} Hope this helps!").
    """
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


class DescriptionService:
    """Generates structured JSON descriptions of functions via OllamaClient."""

    def __init__(self, client: OllamaClient, config: PipelineConfig) -> None:
        self._client = client
        self._model = config.describer_model
        self._allow_gpu = config.allow_gpu
        self._max_source_chars = config.limits.max_description_source_chars
        self._num_ctx = config.limits.describe_num_ctx
        self._timeout_seconds = config.limits.describe_timeout_seconds
        self._describe_concurrency = config.concurrency.describe

    async def describe(self, record: FunctionRecord) -> None:
        """Populate ``record.description`` and ``record.description_status`` in-place.

        Retries once if the response is not valid JSON. Sets description to
        ``None`` on persistent failure so the pipeline continues.
        """
        prompt = _PROMPT_TEMPLATE.format(
            language=record.language,
            file_path=record.file_path,
            qualified_name=record.qualified_name,
            source_code=record.source_code[:self._max_source_chars],
        )
        messages = [{"role": "user", "content": prompt}]

        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                result = await self._client.chat(
                    messages,
                    model=self._model,
                    allow_gpu=self._allow_gpu,
                    num_ctx=self._num_ctx,
                    timeout_seconds=self._timeout_seconds,
                )
                cleaned = _extract_json(result.message)
                json.loads(cleaned)   # validate — raises if not JSON
                record.description = cleaned
                record.description_status = "ok"
                return
            except asyncio.TimeoutError as e:
                last_exc = e
                break  # no point retrying a timeout
            except (RuntimeError, json.JSONDecodeError) as e:
                last_exc = e

        logger.warning(
            "Skipping description for {} ({}): {}",
            record.qualified_name,
            record.file_path,
            last_exc,
        )
        record.description = None
        if isinstance(last_exc, asyncio.TimeoutError):
            record.description_status = "timeout"
        elif isinstance(last_exc, json.JSONDecodeError):
            record.description_status = "invalid_json"
        else:
            record.description_status = "error"

    async def describe_batch(
        self,
        records: list[FunctionRecord],
        on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> None:
        """Generate descriptions for all records in-place, respecting concurrency limit."""
        sem = asyncio.Semaphore(self._describe_concurrency)
        completed = 0

        async def _describe_one(record: FunctionRecord) -> None:
            nonlocal completed
            async with sem:
                await self.describe(record)
                completed += 1
                if on_progress is not None:
                    await on_progress(completed, len(records))

        await asyncio.gather(*[_describe_one(r) for r in records])
