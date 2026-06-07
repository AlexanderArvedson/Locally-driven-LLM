"""Tests for the pipeline reporter.

Pure-function tests (_cosine, _compute_cohesion_scores, _find_previous_report)
run without any mocks. _build_report tests use a flexible stub driver that
returns controlled data for each Cypher query, following the same pattern
as test_neo4j_store.py.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from src.pipeline.contracts import Neo4jConfig, PipelineConfig, ReporterConfig
from src.pipeline.graph.store import Neo4jStore
from src.pipeline.reporting.reporter import _build_report
from src.pipeline.reporting.analysis import _cosine, _compute_cohesion_scores, _find_previous_report


# ---------------------------------------------------------------------------
# Stub driver (matches queries by substring keyword)
# ---------------------------------------------------------------------------

class _StubResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    async def data(self):
        return self._rows

    async def single(self):
        return self._rows[0] if self._rows else None


class _StubSession:
    """Routes each query to the first matching keyword in rows_by_keyword."""

    def __init__(self, rows_by_keyword: dict[str, list]):
        self._rows = rows_by_keyword

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def run(self, query: str, **_kwargs) -> _StubResult:
        for keyword, rows in self._rows.items():
            if keyword in query:
                return _StubResult(rows)
        return _StubResult([])


class _StubDriver:
    def __init__(self, rows_by_keyword: dict[str, list] | None = None):
        self._rows = rows_by_keyword or {}

    def session(self, **_kwargs):
        return _StubSession(self._rows)

    async def close(self):
        pass


def _make_store(rows_by_keyword: dict[str, list] | None = None) -> Neo4jStore:
    config = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="u", password="p")
    store = Neo4jStore(config)
    store._driver = _StubDriver(rows_by_keyword)  # type: ignore[assignment]
    return store


def _minimal_rows() -> dict[str, list]:
    """Minimal stub data that keeps _build_report from crashing on empty results."""
    return {
        # _Q_STATS — must return total and edges
        "WITH count(f) AS total": [{"total": 5, "edges": 2}],
        # _Q_TEST_COUNT
        "isTest: true})\nRETURN count(f) AS test_count": [{"test_count": 0}],
        # _Q_NO_EDGES
        "AND NOT (f)-[:SIMILAR_TO]-()\nRETURN count(f) AS isolated": [{"isolated": 1}],
        # _Q_INTRA_INTER_EDGES
        "AS intra,\n  sum(CASE WHEN a.filePath <> b.filePath": [{"intra": 1, "inter": 1}],
        # _Q_SIMILARITY_DISTRIBUTION
        "AS gt_high,": [{"gt_high": 0, "b_mid_high": 0, "b_low_mid": 0, "lt_low": 0}],
        # everything else → empty list (default)
    }


def _make_pipeline_config(**reporter_kwargs) -> PipelineConfig:
    """Return a minimal PipelineConfig with optional ReporterConfig overrides."""
    from src.pipeline.contracts import (
        SimilarityConfig, ConcurrencyConfig, BatchSizeConfig, LimitsConfig,
    )
    return PipelineConfig(
        repo_path="/tmp/repo",
        repo_name="test-repo",
        supported_languages=["python"],
        ignore_paths=[],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="llama3",
        describer_model="llama3",
        similarity=SimilarityConfig(),
        neo4j=Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="u", password="p"),
        reporter=ReporterConfig(**reporter_kwargs),
    )


# ---------------------------------------------------------------------------
# _cosine tests
# ---------------------------------------------------------------------------

def test_cosine_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert abs(_cosine(v, v) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors():
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_zero_vector_returns_zero():
    # Must not raise ZeroDivisionError.
    assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert _cosine([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_cosine_known_value():
    # [1,1] vs [1,0] → cos(45°) = 1/√2 ≈ 0.7071
    result = _cosine([1.0, 1.0], [1.0, 0.0])
    assert abs(result - 1.0 / math.sqrt(2)) < 1e-6


# ---------------------------------------------------------------------------
# _compute_cohesion_scores tests
# ---------------------------------------------------------------------------

def _row(file: str, name: str, ce=None, de=None, cls=None) -> dict:
    return {
        "filePath": file,
        "className": cls,
        "qualifiedName": name,
        "codeEmbedding": ce,
        "descriptionEmbedding": de,
    }


def test_cohesion_single_function_skipped():
    rows = [_row("a.py", "a.foo", ce=[1.0, 0.0])]
    result = _compute_cohesion_scores(rows, "filePath", 0.7, 0.3, min_functions=2)
    assert result == []


def test_cohesion_two_identical_functions():
    ce = [1.0, 0.0]
    rows = [
        _row("a.py", "a.foo", ce=ce),
        _row("a.py", "a.bar", ce=ce),
    ]
    result = _compute_cohesion_scores(rows, "filePath", 1.0, 0.0, min_functions=2)
    assert len(result) == 1
    assert abs(result[0]["cohesion_score"] - 1.0) < 1e-4


def test_cohesion_two_orthogonal_functions():
    rows = [
        _row("a.py", "a.foo", ce=[1.0, 0.0]),
        _row("a.py", "a.bar", ce=[0.0, 1.0]),
    ]
    result = _compute_cohesion_scores(rows, "filePath", 1.0, 0.0, min_functions=2)
    assert len(result) == 1
    assert abs(result[0]["cohesion_score"]) < 1e-4


def test_cohesion_outlier_detection():
    # foo and bar are identical; baz is orthogonal — baz should be the outlier.
    rows = [
        _row("a.py", "a.foo", ce=[1.0, 0.0]),
        _row("a.py", "a.bar", ce=[1.0, 0.0]),
        _row("a.py", "a.baz", ce=[0.0, 1.0]),
    ]
    result = _compute_cohesion_scores(rows, "filePath", 1.0, 0.0, min_functions=2)
    assert result[0]["outlier"] == "a.baz"


def test_cohesion_sorted_ascending():
    # File A has high cohesion, file B has low — B should appear first.
    rows = [
        _row("high.py", "h.foo", ce=[1.0, 0.0]),
        _row("high.py", "h.bar", ce=[1.0, 0.0]),
        _row("low.py", "l.foo", ce=[1.0, 0.0]),
        _row("low.py", "l.bar", ce=[0.0, 1.0]),
    ]
    result = _compute_cohesion_scores(rows, "filePath", 1.0, 0.0, min_functions=2)
    assert result[0]["group"] == "low.py"
    assert result[-1]["group"] == "high.py"


def test_cohesion_none_className_skipped():
    # Module-level functions have className=None; class cohesion must skip them.
    rows = [
        _row("a.py", "foo", ce=[1.0, 0.0], cls=None),
        _row("a.py", "bar", ce=[1.0, 0.0], cls=None),
    ]
    result = _compute_cohesion_scores(rows, "className", 1.0, 0.0, min_functions=2)
    assert result == []


def test_cohesion_groups_by_class():
    rows = [
        _row("a.py", "A.x", ce=[1.0, 0.0], cls="A"),
        _row("a.py", "A.y", ce=[1.0, 0.0], cls="A"),
        _row("a.py", "B.x", ce=[0.0, 1.0], cls="B"),
        _row("a.py", "B.y", ce=[0.0, 1.0], cls="B"),
    ]
    result = _compute_cohesion_scores(rows, "className", 1.0, 0.0, min_functions=2)
    assert len(result) == 2
    groups = {r["group"] for r in result}
    assert groups == {"A", "B"}


def test_cohesion_no_embeddings_skips_pair():
    # Functions with neither embedding can't contribute a pair score; file skipped.
    rows = [
        _row("a.py", "a.foo"),
        _row("a.py", "a.bar"),
    ]
    result = _compute_cohesion_scores(rows, "filePath", 1.0, 0.0, min_functions=2)
    assert result == []


# ---------------------------------------------------------------------------
# _find_previous_report tests
# ---------------------------------------------------------------------------

def test_find_previous_report_empty_dir(tmp_path):
    assert _find_previous_report(tmp_path) is None


def test_find_previous_report_nonexistent_dir(tmp_path):
    assert _find_previous_report(tmp_path / "does_not_exist") is None


def test_find_previous_report_picks_most_recent(tmp_path):
    older = tmp_path / "20260601-120000"
    older.mkdir()
    newer = tmp_path / "20260605-160935"
    newer.mkdir()

    payload_old = {"timestamp": "old", "stats": {"total_functions": 10}}
    payload_new = {"timestamp": "new", "stats": {"total_functions": 20}}

    (older / "report_20260601-120000.json").write_text(json.dumps(payload_old))
    (newer / "report_20260605-160935.json").write_text(json.dumps(payload_new))

    result = _find_previous_report(tmp_path)
    assert result is not None
    assert result["timestamp"] == "new"


def test_find_previous_report_skips_malformed(tmp_path):
    d = tmp_path / "20260601-120000"
    d.mkdir()
    (d / "report_20260601-120000.json").write_text("not json {{{")

    d2 = tmp_path / "20260605-160935"
    d2.mkdir()
    good = {"timestamp": "good", "stats": {}}
    (d2 / "report_20260605-160935.json").write_text(json.dumps(good))

    result = _find_previous_report(tmp_path)
    assert result is not None
    assert result["timestamp"] == "good"


# ---------------------------------------------------------------------------
# _build_report integration tests (stub driver)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_report_all_sections_present():
    store = _make_store(_minimal_rows())
    lines, _ = await _build_report(store, "test-repo", include_tests=False,
                                   pipeline_config=None, loc_filtered=None,
                                   prev_report=None)
    text = "\n".join(lines)
    for header in [
        "## Metadata",
        "## Delta Since Previous Run",
        "## Embedding Integrity",
        "## Graph Overview",
        "### Isolated Functions",
        "## Similarity Distribution",
        "## Top",
        "## Top",
        "Files by Edge Count",
        "Files by Function Count",
        "## File Cohesion Scores",
        "## Duplication Clusters",
        "## Heuristic Flags",
    ]:
        assert header in text, f"Missing section: {header!r}"


@pytest.mark.asyncio
async def test_build_report_no_delta_when_no_previous():
    store = _make_store(_minimal_rows())
    lines, export = await _build_report(store, "repo", include_tests=False,
                                        pipeline_config=None, loc_filtered=None,
                                        prev_report=None)
    text = "\n".join(lines)
    assert "No previous run found" in text
    assert export["delta"] is None


@pytest.mark.asyncio
async def test_build_report_delta_shown_when_previous_provided():
    prev = {
        "timestamp": "2026-06-05 10:00 UTC",
        "stats": {"total_functions": 100, "edges": 50, "isolated": 10},
        "clusters": [],
    }
    store = _make_store(_minimal_rows())
    lines, export = await _build_report(store, "repo", include_tests=False,
                                        pipeline_config=None, loc_filtered=None,
                                        prev_report=prev)
    text = "\n".join(lines)
    assert "2026-06-05 10:00 UTC" in text
    assert export["delta"] is not None
    assert export["delta"]["functions"] == 5 - 100  # current total=5, prev=100


@pytest.mark.asyncio
async def test_build_report_god_file_flag():
    rows = dict(_minimal_rows())
    # _Q_FILES_BY_FUNCTION_COUNT — keyword: "ORDER BY fn_count DESC"
    rows["ORDER BY fn_count DESC"] = [{"path": "big_file.py", "fn_count": 50}]

    cfg = _make_pipeline_config(god_file_threshold=20)
    store = _make_store(rows)
    lines, export = await _build_report(store, "repo", include_tests=False,
                                        pipeline_config=cfg, loc_filtered=None,
                                        prev_report=None)
    text = "\n".join(lines)
    assert "GOD\\_FILE" in text
    assert "big_file.py" in export["flags"]["GOD_FILE"]


@pytest.mark.asyncio
async def test_build_report_low_cohesion_flag():
    rows = dict(_minimal_rows())
    # _Q_FILE_EMBEDDINGS — keyword unique to that query
    ce_similar = [1.0, 0.0]
    ce_distant = [0.0, 1.0]
    rows["f.codeEmbedding AS codeEmbedding"] = [
        {"filePath": "mixed.py", "className": None, "qualifiedName": "mixed.foo",
         "codeEmbedding": ce_similar, "descriptionEmbedding": None},
        {"filePath": "mixed.py", "className": None, "qualifiedName": "mixed.bar",
         "codeEmbedding": ce_distant, "descriptionEmbedding": None},
    ]

    cfg = _make_pipeline_config(cohesion_low_threshold=0.30, cohesion_min_functions=2)
    store = _make_store(rows)
    _, export = await _build_report(store, "repo", include_tests=False,
                                    pipeline_config=cfg, loc_filtered=None,
                                    prev_report=None)
    assert "mixed.py" in export["flags"]["LOW_COHESION"]


@pytest.mark.asyncio
async def test_build_report_class_cohesion_section_omitted_when_no_classes():
    rows = dict(_minimal_rows())
    rows["f.codeEmbedding AS codeEmbedding"] = [
        {"filePath": "a.py", "className": None, "qualifiedName": "foo",
         "codeEmbedding": [1.0, 0.0], "descriptionEmbedding": None},
        {"filePath": "a.py", "className": None, "qualifiedName": "bar",
         "codeEmbedding": [1.0, 0.0], "descriptionEmbedding": None},
    ]
    store = _make_store(rows)
    lines, export = await _build_report(store, "repo", include_tests=False,
                                        pipeline_config=None, loc_filtered=None,
                                        prev_report=None)
    text = "\n".join(lines)
    assert "## Class Cohesion Scores" not in text
    assert export["class_cohesion"] == []


@pytest.mark.asyncio
async def test_build_report_class_cohesion_section_present_when_classes_exist():
    rows = dict(_minimal_rows())
    rows["f.codeEmbedding AS codeEmbedding"] = [
        {"filePath": "a.py", "className": "MyClass", "qualifiedName": "MyClass.foo",
         "codeEmbedding": [1.0, 0.0], "descriptionEmbedding": None},
        {"filePath": "a.py", "className": "MyClass", "qualifiedName": "MyClass.bar",
         "codeEmbedding": [1.0, 0.0], "descriptionEmbedding": None},
    ]
    store = _make_store(rows)
    lines, export = await _build_report(store, "repo", include_tests=False,
                                        pipeline_config=None, loc_filtered=None,
                                        prev_report=None)
    text = "\n".join(lines)
    assert "## Class Cohesion Scores" in text
    assert len(export["class_cohesion"]) == 1


@pytest.mark.asyncio
async def test_build_report_json_export_has_all_keys():
    store = _make_store(_minimal_rows())
    _, export = await _build_report(store, "repo", include_tests=False,
                                    pipeline_config=None, loc_filtered=None,
                                    prev_report=None)
    for key in [
        "repo", "timestamp", "pipeline_version", "embedding_model",
        "delta", "stats", "embedding", "similarity_distribution",
        "isolated_functions", "files_by_function_count",
        "file_cohesion", "class_cohesion",
        "clusters", "failures", "top_pairs", "flags",
    ]:
        assert key in export, f"Missing JSON export key: {key!r}"

    for flag_key in ["HIGH_DUPLICATION_CLUSTER", "CROSS_FILE_DUPLICATION",
                     "ARCHITECTURE_COUPLING", "TEST_POLLUTION",
                     "LOW_COHESION", "GOD_FILE"]:
        assert flag_key in export["flags"], f"Missing flag key: {flag_key!r}"
