"""Unit tests for _build_report_blocks in slack_notifier.

_build_report_blocks is a pure function — no mocks needed.
"""

import pytest

from src.api.slack_notifier import _build_report_blocks


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def full_data() -> dict:
    return {
        "repo": "monorepo",
        "timestamp": "2026-06-05 14:41 CEST",
        "stats": {
            "total_functions": 321,
            "edges": 200,
            "density": 0.6231,
            "intra_edges": 97,
            "inter_edges": 103,
        },
        "embedding": {
            "code": {
                "ok": 312,
                "context_overflow": 8,
                "error": 1,
                "failed_total": 9,
            }
        },
        "similarity_distribution": {"gt95": 12, "b90_95": 23, "b80_90": 165},
        "clusters": [
            {
                "id": 1,
                "size": 5,
                "max_score": 1.0,
                "avg_score": 0.963,
                "representative": "GamepadDriver.last_emitted",
            }
        ],
        "top_pairs": [
            {
                "a_name": "KeyboardDriver.last_emitted",
                "b_name": "WindowsGamepadDriver.last_emitted",
                "score": 1.0,
            }
        ],
        "flags": {
            "HIGH_DUPLICATION_CLUSTER": [1],
            "CROSS_FILE_DUPLICATION": [1, 2],
            "ARCHITECTURE_COUPLING": ["modules/drivers/gamepad.py"],
            "TEST_POLLUTION": None,
        },
    }


def _all_text(blocks: list) -> str:
    """Concatenate all text values from a block list for easy assertion."""
    parts = []
    for block in blocks:
        text = block.get("text", {})
        if isinstance(text, dict):
            parts.append(text.get("text", ""))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def test_build_report_blocks_header(full_data):
    blocks = _build_report_blocks(full_data)
    assert blocks[0]["type"] == "header"
    assert "monorepo" in blocks[0]["text"]["text"]
    assert "2026-06-05 14:41 CEST" in blocks[0]["text"]["text"]


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def test_build_report_blocks_overview_fields(full_data):
    text = _all_text(_build_report_blocks(full_data))
    assert "321" in text   # total_functions
    assert "200" in text   # edges
    assert "0.62" in text  # density
    assert "97" in text    # intra_edges
    assert "103" in text   # inter_edges


# ---------------------------------------------------------------------------
# Embedding health
# ---------------------------------------------------------------------------


def test_build_report_blocks_embedding_health(full_data):
    text = _all_text(_build_report_blocks(full_data))
    assert "312" in text  # ok
    assert "9" in text    # failed_total
    assert "8" in text    # context_overflow
    assert "1" in text    # error


# ---------------------------------------------------------------------------
# Similarity bands
# ---------------------------------------------------------------------------


def test_build_report_blocks_similarity_bands(full_data):
    text = _all_text(_build_report_blocks(full_data))
    assert "12" in text   # gt95
    assert "23" in text   # b90_95
    assert "165" in text  # b80_90


# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------


def test_build_report_blocks_cluster_block(full_data):
    text = _all_text(_build_report_blocks(full_data))
    assert "GamepadDriver.last_emitted" in text
    assert "5" in text      # size
    assert "0.963" in text  # avg_score


def test_build_report_blocks_no_clusters_omits_block(full_data):
    full_data["clusters"] = []
    text = _all_text(_build_report_blocks(full_data))
    # The cluster block specifically renders "Largest:" — absent when clusters is empty
    assert "Largest:" not in text
    assert "duplication clusters" not in text


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------


def test_build_report_blocks_flags_raised(full_data):
    text = _all_text(_build_report_blocks(full_data))
    assert "HIGH_DUPLICATION_CLUSTER" in text
    assert "CROSS_FILE_DUPLICATION" in text
    assert "ARCHITECTURE_COUPLING" in text


def test_build_report_blocks_no_flags_omits_block(full_data):
    full_data["flags"] = {
        "HIGH_DUPLICATION_CLUSTER": [],
        "CROSS_FILE_DUPLICATION": [],
        "ARCHITECTURE_COUPLING": [],
        "TEST_POLLUTION": None,
    }
    text = _all_text(_build_report_blocks(full_data))
    assert "HIGH_DUPLICATION_CLUSTER" not in text
    assert "\U0001f6a8" not in text


def test_build_report_blocks_test_pollution_flag(full_data):
    full_data["flags"]["TEST_POLLUTION"] = 3
    text = _all_text(_build_report_blocks(full_data))
    assert "TEST_POLLUTION" in text


# ---------------------------------------------------------------------------
# Top pair
# ---------------------------------------------------------------------------


def test_build_report_blocks_top_pair(full_data):
    text = _all_text(_build_report_blocks(full_data))
    assert "KeyboardDriver.last_emitted" in text
    assert "WindowsGamepadDriver.last_emitted" in text
    assert "1.0000" in text


def test_build_report_blocks_no_top_pairs_omits_block(full_data):
    full_data["top_pairs"] = []
    text = _all_text(_build_report_blocks(full_data))
    assert "Top pair" not in text
