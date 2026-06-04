"""Description service for LLM-generated function summaries.

Wraps ``OllamaClient.chat()`` to produce structured JSON descriptions of
extracted functions. Retries once on invalid JSON before giving up.
"""

from __future__ import annotations

import asyncio
import json
import re

from loguru import logger

from src.core.ollama_client import OllamaClient
from src.pipeline.contracts import FunctionRecord, PipelineConfig

_PROMPT_TEMPLATE = """\
You are analyzing source code for a code intelligence system.

Describe the following {language} function. Respond with a JSON object ONLY — \
no markdown, no explanation, no code fences.

Required fields:
- summary: one or two sentences describing what the function does
- inputs: list of important parameters or inputs
- outputs: what the function returns or produces
- sideEffects: list of external effects (db writes, network calls, mutations, I/O, logging)
- errors: notable exceptions or error cases handled or raised
- dependencies: important internal or external functions, services, or libraries used

Function metadata:
  Language: {language}
  File: {file_path}
  Name: {qualified_name}

Source code:
{source_code}"""


def _strip_fences(text: str) -> str:
    """Remove triple-backtick code fences that models emit despite instructions."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


class DescriptionService:
    """Generates structured JSON descriptions of functions via OllamaClient."""

    def __init__(self, client: OllamaClient, config: PipelineConfig) -> None:
        self._client = client
        self._model = config.describer_model
        self._allow_gpu = config.allow_gpu
        self._max_source_chars = config.limits.max_description_source_chars
        self._describe_concurrency = config.concurrency.describe

    async def describe(self, record: FunctionRecord) -> None:
        """Populate ``record.description`` in-place with a JSON string.

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

        for attempt in range(2):
            try:
                result = await self._client.chat(
                    messages,
                    model=self._model,
                    allow_gpu=self._allow_gpu,
                )
                cleaned = _strip_fences(result.message)
                json.loads(cleaned)   # validate — raises if not JSON
                record.description = cleaned
                return
            except (RuntimeError, json.JSONDecodeError) as e:
                if attempt == 1:
                    logger.warning(
                        "Skipping description for {} ({}): {}",
                        record.qualified_name,
                        record.file_path,
                        e,
                    )
                    record.description = None

    async def describe_batch(self, records: list[FunctionRecord]) -> None:
        """Generate descriptions for all records in-place, respecting concurrency limit."""
        sem = asyncio.Semaphore(self._describe_concurrency)

        async def _describe_one(record: FunctionRecord) -> None:
            async with sem:
                await self.describe(record)

        await asyncio.gather(*[_describe_one(r) for r in records])
