"""Unit tests for the LOC threshold filter in EmbeddingPipeline.

The filter runs in Stage 2b, after extraction and before any Ollama or
Neo4j work. Tests stub out FunctionExtractor, Neo4jStore, and OllamaClient
so no real services are needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.contracts import (
    FunctionRecord,
    LimitsConfig,
    Neo4jConfig,
    PipelineConfig,
    SimilarityConfig,
)
from src.pipeline.pipeline import EmbeddingPipeline

_NEO4J = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="pw")
_SIM = SimilarityConfig()


def _make_config(min_loc_threshold: int = 0) -> PipelineConfig:
    return PipelineConfig(
        repo_path="/tmp/fake-repo",
        repo_name="test-repo",
        supported_languages=["python"],
        ignore_paths=[],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="qwen2.5-coder:7b",
        describer_model="qwen2.5:7b",
        similarity=_SIM,
        neo4j=_NEO4J,
        limits=LimitsConfig(min_loc_threshold=min_loc_threshold),
    )


def _make_record(name: str, start_line: int, end_line: int) -> FunctionRecord:
    """Build a minimal FunctionRecord with the given line range."""
    import hashlib
    source = f"def {name}(): pass"
    return FunctionRecord(
        id=hashlib.sha256(f"test-repo:fake.py:{name}".encode()).hexdigest(),
        repo="test-repo",
        language="python",
        file_path="fake.py",
        function_name=name,
        qualified_name=name,
        class_name=None,
        start_line=start_line,
        end_line=end_line,
        source_code=source,
        source_hash=hashlib.sha256(source.encode()).hexdigest(),
    )


def _make_pipeline(config: PipelineConfig) -> EmbeddingPipeline:
    with (
        patch("src.pipeline.pipeline.OllamaClient"),
        patch("src.pipeline.pipeline.Neo4jStore"),
    ):
        return EmbeddingPipeline(config, dry_run=True)


@pytest.mark.asyncio
async def test_no_filter_when_threshold_is_zero():
    """threshold=0 disables filtering; all extracted functions are kept."""
    config = _make_config(min_loc_threshold=0)
    pipeline = _make_pipeline(config)

    records = [
        _make_record("tiny", 1, 1),   # 1 LOC
        _make_record("small", 1, 3),  # 3 LOC
    ]

    with patch.object(pipeline._extractor, "extract_all", return_value=records):
        pipeline._store.get_existing_hashes = AsyncMock(return_value={})
        result = await pipeline.run()

    assert result.loc_filtered == 0
    assert result.total_extracted == 2


@pytest.mark.asyncio
async def test_filter_removes_short_functions():
    """Functions with LOC < threshold are excluded; loc_filtered is set correctly."""
    config = _make_config(min_loc_threshold=5)
    pipeline = _make_pipeline(config)

    records = [
        _make_record("one_liner", 1, 1),   # 1 LOC  — filtered
        _make_record("short_fn", 1, 3),    # 3 LOC  — filtered
        _make_record("exact_threshold", 1, 5),  # 5 LOC — kept (>= threshold)
        _make_record("long_fn", 1, 10),    # 10 LOC — kept
    ]

    with patch.object(pipeline._extractor, "extract_all", return_value=records):
        pipeline._store.get_existing_hashes = AsyncMock(return_value={})
        result = await pipeline.run()

    assert result.loc_filtered == 2
    assert result.total_extracted == 4


@pytest.mark.asyncio
async def test_filter_keeps_all_when_all_above_threshold():
    """When all functions meet the threshold nothing is filtered."""
    config = _make_config(min_loc_threshold=3)
    pipeline = _make_pipeline(config)

    records = [
        _make_record("fn_a", 1, 5),   # 5 LOC
        _make_record("fn_b", 10, 15), # 6 LOC
    ]

    with patch.object(pipeline._extractor, "extract_all", return_value=records):
        pipeline._store.get_existing_hashes = AsyncMock(return_value={})
        result = await pipeline.run()

    assert result.loc_filtered == 0
    assert result.total_extracted == 2


@pytest.mark.asyncio
async def test_single_line_function_counts_as_one_loc():
    """A function where start_line == end_line has exactly 1 LOC."""
    config = _make_config(min_loc_threshold=2)
    pipeline = _make_pipeline(config)

    records = [
        _make_record("one_liner", 5, 5),  # 1 LOC — filtered
        _make_record("two_liner", 7, 8),  # 2 LOC — kept
    ]

    with patch.object(pipeline._extractor, "extract_all", return_value=records):
        pipeline._store.get_existing_hashes = AsyncMock(return_value={})
        result = await pipeline.run()

    assert result.loc_filtered == 1
    assert result.total_extracted == 2


@pytest.mark.asyncio
async def test_total_extracted_reflects_prefilter_count():
    """total_extracted always reflects what the extractor returned, not the filtered count."""
    config = _make_config(min_loc_threshold=10)
    pipeline = _make_pipeline(config)

    records = [_make_record(f"fn_{i}", 1, i + 1) for i in range(5)]  # 1–5 LOC each

    with patch.object(pipeline._extractor, "extract_all", return_value=records):
        pipeline._store.get_existing_hashes = AsyncMock(return_value={})
        result = await pipeline.run()

    assert result.total_extracted == 5
    assert result.loc_filtered == 5  # all below threshold of 10
