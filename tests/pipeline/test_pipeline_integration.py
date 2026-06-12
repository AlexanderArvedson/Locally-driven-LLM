"""End-to-end integration test for EmbeddingPipeline.

All external I/O is stubbed:
- OllamaClient.chat / embed  → fixed responses
- Neo4jStore driver          → stub that records queries and returns controlled data

This validates that the pipeline stages run in the correct order and that
incremental processing (skip unchanged functions) works correctly.
"""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.core.ollama_client import EmbedResult, LLMResult, OllamaClient
from src.pipeline.contracts import Neo4jConfig, PipelineConfig, SimilarityConfig
from src.pipeline.pipeline import EmbeddingPipeline

_NEO4J = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="pw")

_VALID_DESC = json.dumps({
    "summary": "A test function.",
    "inputs": [],
    "outputs": "None",
    "sideEffects": [],
    "errors": [],
    "dependencies": [],
})


def _make_config(repo_path: str) -> PipelineConfig:
    return PipelineConfig(
        repo_path=repo_path,
        repo_name="test-repo",
        supported_languages=["python"],
        ignore_paths=[".venv", "__pycache__"],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="qwen2.5-coder:7b",
        describer_model="qwen2.5-coder:7b",
        similarity=SimilarityConfig(threshold=0.5, top_n=5),
        neo4j=_NEO4J,
    )


def _write_functions(root: Path, count: int) -> None:
    lines = [f"def func_{i}(): pass\n" for i in range(count)]
    (root / "funcs.py").write_text("".join(lines))


def _patch_ollama(monkeypatch) -> None:
    async def fake_embed(self, text, model, **kwargs):
        # Use text hash to make embeddings distinct (but deterministic).
        seed = hashlib.sha256(text.encode()).digest()
        vec = [(b / 255.0) for b in seed[:8]] + [0.0] * 0
        # Pad to length 8 for simplicity.
        return EmbedResult(embedding=vec)

    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message=_VALID_DESC, input_tokens=10, output_tokens=20)

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)
    monkeypatch.setattr(OllamaClient, "chat", fake_chat)


@pytest.mark.asyncio
async def test_first_run_processes_all_functions(monkeypatch):
    _patch_ollama(monkeypatch)

    with tempfile.TemporaryDirectory() as tmp:
        _write_functions(Path(tmp), 3)
        config = _make_config(tmp)
        pipeline = EmbeddingPipeline(config, dry_run=True)

        # Patch store so no real Neo4j needed.
        pipeline._store.get_existing_hashes = AsyncMock(return_value={})
        pipeline._store.ensure_schema = AsyncMock()
        pipeline._store.upsert_functions_batch = AsyncMock()
        pipeline._store.delete_missing = AsyncMock(return_value=0)
        pipeline._store.get_all_embeddings = AsyncMock(return_value=[])
        pipeline._store.upsert_similarity_edges_batch = AsyncMock()

        result = await pipeline.run()

    assert result.total_extracted == 3
    assert result.changed == 3
    assert result.unchanged == 0
    assert not result.errors


@pytest.mark.asyncio
async def test_second_run_skips_unchanged_functions(monkeypatch):
    embed_call_count = 0

    async def counting_embed(self, text, model, **kwargs):
        nonlocal embed_call_count
        embed_call_count += 1
        return EmbedResult(embedding=[0.1] * 8)

    async def fake_chat(self, messages, model, **kwargs):
        return LLMResult(message=_VALID_DESC, input_tokens=0, output_tokens=0)

    monkeypatch.setattr(OllamaClient, "embed", counting_embed)
    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    with tempfile.TemporaryDirectory() as tmp:
        _write_functions(Path(tmp), 3)
        config = _make_config(tmp)
        pipeline = EmbeddingPipeline(config, dry_run=True)

        # Simulate Neo4j already having all three functions with matching hashes.
        from src.pipeline.extraction.extractor import FunctionExtractor, _source_hash
        records = FunctionExtractor(config).extract_all()
        existing = {r.id: r.source_hash for r in records}

        pipeline._store.get_existing_hashes = AsyncMock(return_value=existing)
        pipeline._store.ensure_schema = AsyncMock()
        pipeline._store.upsert_functions_batch = AsyncMock()
        pipeline._store.delete_missing = AsyncMock(return_value=0)
        pipeline._store.get_all_embeddings = AsyncMock(return_value=[])
        pipeline._store.upsert_similarity_edges_batch = AsyncMock()

        result = await pipeline.run()

    assert result.unchanged == 3
    assert result.changed == 0
    assert embed_call_count == 0   # no Ollama calls for unchanged functions
