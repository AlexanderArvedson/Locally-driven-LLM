import asyncio
import hashlib

import pytest

from src.core.ollama_client import EmbedResult, OllamaClient
from src.pipeline.contracts import ConcurrencyConfig, FunctionRecord, Neo4jConfig, PipelineConfig, SimilarityConfig
from src.pipeline.embedder import EmbeddingService

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
