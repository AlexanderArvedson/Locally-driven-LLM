import hashlib
import json

import pytest

from src.core.ollama_client import LLMResult, OllamaClient
from src.pipeline.contracts import FunctionRecord, Neo4jConfig, PipelineConfig, SimilarityConfig
from src.pipeline.descriptions.service import DescriptionService, _extract_json

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
        describer_model="qwen2.5-coder:7b",
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


def test_extract_json_removes_markdown_fences():
    wrapped = "```json\n{\"key\": 1}\n```"
    assert _extract_json(wrapped) == '{"key": 1}'


def test_extract_json_no_fences_unchanged():
    raw = '{"key": 1}'
    assert _extract_json(raw) == raw


def test_extract_json_strips_surrounding_prose():
    prose = 'Here is the description:\n{"key": 1}\nHope this helps!'
    assert _extract_json(prose) == '{"key": 1}'


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


@pytest.mark.asyncio
async def test_describe_sets_ok_status_on_success(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message=_VALID_JSON, input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()
    await service.describe(record)

    assert record.description_status == "ok"


@pytest.mark.asyncio
async def test_describe_sets_invalid_json_status_on_persistent_bad_json(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message="not json", input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()
    await service.describe(record)

    assert record.description_status == "invalid_json"
    assert record.description is None


@pytest.mark.asyncio
async def test_describe_sets_error_status_on_runtime_error(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        raise RuntimeError("Ollama chat request failed: 500")

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()
    await service.describe(record)

    assert record.description_status == "error"
    assert record.description is None


@pytest.mark.asyncio
async def test_describe_sets_timeout_status(monkeypatch):
    import asyncio

    async def fake_chat(self, messages, model, **kwargs):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    record = _make_record()
    await service.describe(record)

    assert record.description_status == "timeout"
    assert record.description is None


@pytest.mark.asyncio
async def test_describe_batch_calls_on_progress_per_item(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message=_VALID_JSON, input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    records = [_make_record() for _ in range(4)]
    # Give each record a unique id so they don't alias
    for i, r in enumerate(records):
        r.id = f"id{i}"

    calls: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int) -> None:
        calls.append((done, total))

    await service.describe_batch(records, on_progress=on_progress)

    assert len(calls) == 4
    assert calls[-1] == (4, 4)


@pytest.mark.asyncio
async def test_describe_batch_no_progress_when_callback_is_none(monkeypatch):
    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message=_VALID_JSON, input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    client = OllamaClient("http://localhost:11434")
    service = DescriptionService(client, _make_config())
    records = [_make_record()]
    # Should not raise
    await service.describe_batch(records, on_progress=None)
