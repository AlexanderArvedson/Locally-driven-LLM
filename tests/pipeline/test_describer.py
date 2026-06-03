import hashlib
import json

import pytest

from src.core.ollama_client import LLMResult, OllamaClient
from src.pipeline.contracts import FunctionRecord, Neo4jConfig, PipelineConfig, SimilarityConfig
from src.pipeline.describer import DescriptionService, _strip_fences

_NEO4J = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="pw")

_VALID_JSON = json.dumps({
    "summary": "Returns the sum of two numbers.",
    "inputs": ["a: int", "b: int"],
    "outputs": "int",
    "sideEffects": [],
    "errors": [],
    "dependencies": [],
})


def _make_config() -> PipelineConfig:
    return PipelineConfig(
        repo_path="/tmp",
        repo_name="repo",
        supported_languages=["python"],
        ignore_paths=[],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="qwen2.5-coder:7b",
        similarity=SimilarityConfig(),
        neo4j=_NEO4J,
    )


def _make_record() -> FunctionRecord:
    src = "def add(a, b): return a + b"
    return FunctionRecord(
        id="id1",
        repo="repo",
        language="python",
        file_path="math.py",
        function_name="add",
        qualified_name="add",
        class_name=None,
        start_line=1,
        end_line=1,
        source_code=src,
        source_hash=hashlib.sha256(src.encode()).hexdigest(),
    )


def test_strip_fences_removes_markdown():
    wrapped = "```json\n{\"key\": 1}\n```"
    assert _strip_fences(wrapped) == '{"key": 1}'


def test_strip_fences_no_fences_unchanged():
    raw = '{"key": 1}'
    assert _strip_fences(raw) == raw


@pytest.mark.asyncio
async def test_describe_populates_description(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message=_VALID_JSON, input_tokens=10, output_tokens=20)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()

    await service.describe(record)

    assert record.description is not None
    parsed = json.loads(record.description)
    assert "summary" in parsed


@pytest.mark.asyncio
async def test_describe_retries_on_invalid_json(monkeypatch):
    call_count = 0

    async def fake_chat(self, messages, model, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResult(message="not json at all", input_tokens=0, output_tokens=0)
        return LLMResult(message=_VALID_JSON, input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()

    await service.describe(record)

    assert call_count == 2
    assert record.description is not None


@pytest.mark.asyncio
async def test_describe_sets_none_on_persistent_failure(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message="still not json", input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()

    await service.describe(record)

    assert record.description is None
