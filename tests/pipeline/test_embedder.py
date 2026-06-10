import asyncio
import hashlib

import pytest

from src.core.ollama_client import EmbedResult, OllamaClient
from src.pipeline.contracts import ConcurrencyConfig, FunctionRecord, Neo4jConfig, PipelineConfig, SimilarityConfig
from src.pipeline.embeddings.service import EmbeddingService

_NEO4J = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="pw")


def _make_config(concurrency: ConcurrencyConfig | None = None) -> PipelineConfig:
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
        concurrency=concurrency or ConcurrencyConfig(),
    )


def _make_record(source_code: str = "def foo(): pass") -> FunctionRecord:
    return FunctionRecord(
        id="id1",
        repo="repo",
        language="python",
        file_path="foo.py",
        function_name="foo",
        qualified_name="foo",
        class_name=None,
        start_line=1,
        end_line=1,
        source_code=source_code,
        source_hash=hashlib.sha256(source_code.encode()).hexdigest(),
    )


@pytest.mark.asyncio
async def test_embed_code_populates_embedding(monkeypatch):
    call_count = 0

    async def fake_embed(self, text, model, **kwargs):
        nonlocal call_count
        call_count += 1
        return EmbedResult(embedding=[0.5] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record()

    await service.embed_code(record)

    assert record.code_embedding == [0.5] * 768
    assert call_count == 1


@pytest.mark.asyncio
async def test_embed_code_skips_empty_source(monkeypatch):
    call_count = 0

    async def fake_embed(self, text, model, **kwargs):
        nonlocal call_count
        call_count += 1
        return EmbedResult(embedding=[0.1] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record(source_code="   ")

    await service.embed_code(record)

    assert record.code_embedding is None
    assert call_count == 0


@pytest.mark.asyncio
async def test_embed_batch_respects_concurrency(monkeypatch):
    active = 0
    max_active = 0

    async def fake_embed(self, text, model, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1
        return EmbedResult(embedding=[0.1] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    config = _make_config(concurrency=ConcurrencyConfig(embed_code=3))
    service = EmbeddingService(client, config)
    records = [_make_record(f"def f{i}(): pass") for i in range(10)]

    await service.embed_code_batch(records)

    assert max_active <= 3
    assert all(r.code_embedding is not None for r in records)


@pytest.mark.asyncio
async def test_embed_code_sets_ok_status(monkeypatch):
    monkeypatch.setattr(OllamaClient, "embed", lambda self, text, model, **kw: _fake_embed_ok())

    async def _fake_embed_ok():
        return EmbedResult(embedding=[0.1] * 768)

    monkeypatch.setattr(OllamaClient, "embed", lambda self, text, model, **kw: _fake_embed_ok())

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record()
    await service.embed_code(record)

    assert record.code_embedding_status == "ok"
    assert record.code_embedding_input_chars is None


@pytest.mark.asyncio
async def test_embed_code_skipped_status_on_empty_source(monkeypatch):
    monkeypatch.setattr(OllamaClient, "embed", lambda self, text, model, **kw: (_ for _ in ()).throw(AssertionError("should not be called")))

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record(source_code="   ")
    await service.embed_code(record)

    assert record.code_embedding_status == "skipped"


@pytest.mark.asyncio
async def test_embed_code_error_status_when_chunked_embed_fails(monkeypatch):
    async def fail_embed(self, text, model, **kw):
        raise RuntimeError("Ollama embed request failed: 500")

    monkeypatch.setattr(OllamaClient, "embed", fail_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    # Large input routes through _embed_chunked; if chunking fails it becomes "error"
    record = _make_record(source_code="x" * 15_000)
    await service.embed_code(record)

    assert record.code_embedding_status == "error"
    assert record.code_embedding_input_chars == 15_000


@pytest.mark.asyncio
async def test_embed_code_error_status_on_small_input_failure(monkeypatch):
    async def fail_embed(self, text, model, **kw):
        raise RuntimeError("Ollama embed request failed: 500")

    monkeypatch.setattr(OllamaClient, "embed", fail_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record(source_code="def foo(): pass")
    await service.embed_code(record)

    assert record.code_embedding_status == "error"
    assert record.code_embedding_input_chars is not None


@pytest.mark.asyncio
async def test_embed_code_timeout_status(monkeypatch):
    async def timeout_embed(self, text, model, **kw):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(OllamaClient, "embed", timeout_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record()
    await service.embed_code(record)

    assert record.code_embedding_status == "timeout"


@pytest.mark.asyncio
async def test_embed_description_extracts_summary(monkeypatch):
    import json

    async def fake_embed(self, text, model, **kwargs):
        return EmbedResult(embedding=[float(len(text))])  # encode length as signal

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record()
    record.description = json.dumps({"summary": "does something", "inputs": [], "outputs": "None"})

    await service.embed_description(record)

    # Embedding was generated from "does something", not the full JSON.
    assert record.description_embedding == [float(len("does something"))]


@pytest.mark.asyncio
async def test_embed_code_batch_calls_on_progress_per_item(monkeypatch):
    async def fake_embed(self, text, model, **kwargs):
        return EmbedResult(embedding=[0.1] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    records = [_make_record(f"def f{i}(): pass") for i in range(5)]

    calls: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int) -> None:
        calls.append((done, total))

    await service.embed_code_batch(records, on_progress=on_progress)

    assert len(calls) == 5
    assert calls[-1] == (5, 5)


@pytest.mark.asyncio
async def test_embed_code_batch_no_progress_when_callback_is_none(monkeypatch):
    async def fake_embed(self, text, model, **kwargs):
        return EmbedResult(embedding=[0.1] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    records = [_make_record()]
    # Should not raise
    await service.embed_code_batch(records, on_progress=None)


@pytest.mark.asyncio
async def test_embed_description_batch_calls_on_progress_per_item(monkeypatch):
    async def fake_embed(self, text, model, **kwargs):
        return EmbedResult(embedding=[0.2] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    import json
    records = [_make_record() for _ in range(3)]
    for r in records:
        r.description = json.dumps({"summary": "x"})

    calls: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int) -> None:
        calls.append((done, total))

    await service.embed_description_batch(records, on_progress=on_progress)

    assert len(calls) == 3
    assert calls[-1] == (3, 3)


def test_chunk_source_produces_correct_windows():
    # 7 000-char text → 2 chunks with defaults (size=6 000, overlap=600, step=5 400)
    service = EmbeddingService(OllamaClient("http://localhost:11434"), _make_config())
    text = "a" * 7_000
    chunks = service._chunk_source(text)

    assert len(chunks) == 2
    assert all(len(c) <= 6_000 for c in chunks)
    # Adjacent chunks share the 600-char overlap
    assert chunks[0][-600:] == chunks[1][:600]
    # No content is dropped — removing the repeated overlap reconstructs original
    assert chunks[0] + chunks[1][600:] == text


@pytest.mark.asyncio
async def test_embed_chunked_returns_mean_of_chunk_embeddings(monkeypatch):
    # 7 000-char text → exactly 2 chunks with defaults
    call_results = [[1.0, 0.0], [0.0, 1.0]]
    call_index = 0

    async def fake_embed(self, text, model, **kwargs):
        nonlocal call_index
        result = call_results[call_index % len(call_results)]
        call_index += 1
        return EmbedResult(embedding=result)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    service = EmbeddingService(OllamaClient("http://localhost:11434"), _make_config())
    result = await service._embed_chunked("a" * 7_000)

    assert call_index == 2
    assert result == [0.5, 0.5]


@pytest.mark.asyncio
async def test_embed_code_uses_chunked_path_for_large_input(monkeypatch):
    call_count = 0

    async def fake_embed(self, text, model, **kwargs):
        nonlocal call_count
        call_count += 1
        return EmbedResult(embedding=[0.5] * 768)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)

    client = OllamaClient("http://localhost:11434")
    service = EmbeddingService(client, _make_config())
    record = _make_record(source_code="x" * 10_000)  # >= context_overflow_char_threshold

    await service.embed_code(record)

    assert record.code_embedding is not None
    assert record.code_embedding_status == "chunked"
    assert call_count > 1  # multiple chunks were embedded
