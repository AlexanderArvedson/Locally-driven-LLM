"""Tests for the pipeline checkpoint system."""

import hashlib
import json

import pytest

import src.pipeline.checkpoint as checkpoint_module
from src.pipeline.checkpoint import CheckpointManager, make_run_key
from src.pipeline.contracts import CheckpointConfig, FunctionRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chk_dir(tmp_path, monkeypatch):
    """Redirect _CHECKPOINT_DIR to a temp directory so tests don't touch the real one."""
    monkeypatch.setattr(checkpoint_module, "_CHECKPOINT_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(enabled: bool = True, interval: int = 5) -> CheckpointConfig:
    return CheckpointConfig(enabled=enabled, interval=interval)


def _record(id: str = "r1", description: str | None = None, description_status: str | None = None,
            code_embedding: list[float] | None = None, code_embedding_status: str | None = None,
            description_embedding: list[float] | None = None) -> FunctionRecord:
    return FunctionRecord(
        id=id,
        repo="testrepo",
        language="python",
        file_path="foo.py",
        function_name="foo",
        qualified_name="foo",
        class_name=None,
        start_line=1,
        end_line=5,
        source_code="def foo(): pass",
        source_hash=hashlib.sha256(b"def foo(): pass").hexdigest(),
        description=description,
        description_status=description_status,
        code_embedding=code_embedding,
        code_embedding_status=code_embedding_status,
        description_embedding=description_embedding,
    )


# ---------------------------------------------------------------------------
# make_run_key
# ---------------------------------------------------------------------------

def test_make_run_key_stable():
    """Same record IDs always produce the same key."""
    records = [_record("a"), _record("b"), _record("c")]
    assert make_run_key(records) == make_run_key(records)


def test_make_run_key_order_independent():
    """Key must not depend on list order."""
    r1, r2, r3 = _record("a"), _record("b"), _record("c")
    assert make_run_key([r1, r2, r3]) == make_run_key([r3, r1, r2])


def test_make_run_key_changes_with_different_ids():
    """Different changed sets must produce different keys."""
    assert make_run_key([_record("a")]) != make_run_key([_record("b")])


def test_make_run_key_length():
    """Key is exactly 12 hex chars."""
    key = make_run_key([_record("x")])
    assert len(key) == 12
    assert all(c in "0123456789abcdef" for c in key)


# ---------------------------------------------------------------------------
# load — missing / stale / corrupt
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_no_file(chk_dir):
    mgr = CheckpointManager(_cfg())
    assert mgr.load("repo", "aabbccddeeff") == {}


def test_load_returns_empty_when_run_key_mismatch(chk_dir):
    """File exists but belongs to a different run — should be ignored."""
    mgr = CheckpointManager(_cfg())
    records = [_record("r1")]
    run_key = make_run_key(records)
    mgr.save("repo", run_key, records)
    assert mgr.load("repo", "000000000000") == {}


def test_load_returns_empty_when_json_corrupt(chk_dir):
    """Corrupt checkpoint file must not crash the pipeline."""
    (chk_dir / "repo_aabbccddeeff.json").write_text("{ not valid json }")
    assert CheckpointManager(_cfg()).load("repo", "aabbccddeeff") == {}


def test_load_returns_empty_when_disabled(chk_dir):
    """Disabled checkpoint must always return {} even if a file exists."""
    mgr = CheckpointManager(_cfg())
    records = [_record("r1", description_status="ok")]
    run_key = make_run_key(records)
    mgr.save("repo", run_key, records)  # write a real checkpoint first
    assert CheckpointManager(_cfg(enabled=False)).load("repo", run_key) == {}


# ---------------------------------------------------------------------------
# save → load round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_restores_chunked_status(chk_dir):
    """'chunked' is a terminal success state and must survive a save/load cycle."""
    mgr = CheckpointManager(_cfg())
    r = _record("r1", code_embedding_status="chunked", code_embedding=[0.1, 0.2])
    run_key = make_run_key([r])
    mgr.save("repo", run_key, [r])
    saved = mgr.load("repo", run_key)
    assert saved["r1"]["code_embedding_status"] == "chunked"


def test_save_and_load_restores_all_fields(chk_dir):
    """All five expensive fields survive a save/load cycle."""
    mgr = CheckpointManager(_cfg())
    r = _record(
        id="r1",
        description='{"summary": "does a thing"}',
        description_status="ok",
        code_embedding=[0.1, 0.2],
        code_embedding_status="ok",
        description_embedding=[0.3, 0.4],
    )
    run_key = make_run_key([r])
    mgr.save("myrepo", run_key, [r])

    saved = mgr.load("myrepo", run_key)
    assert saved["r1"]["description"] == '{"summary": "does a thing"}'
    assert saved["r1"]["description_status"] == "ok"
    assert saved["r1"]["code_embedding"] == [0.1, 0.2]
    assert saved["r1"]["code_embedding_status"] == "ok"
    assert saved["r1"]["description_embedding"] == [0.3, 0.4]


def test_save_only_stores_expensive_fields(chk_dir):
    """Checkpoint must not store source_code or other heavyweight fields."""
    mgr = CheckpointManager(_cfg())
    r = _record("r1", description_status="ok")
    run_key = make_run_key([r])
    mgr.save("repo", run_key, [r])

    raw = json.loads((chk_dir / f"repo_{run_key}.json").read_text())
    assert "source_code" not in raw["records"]["r1"]
    assert "file_path" not in raw["records"]["r1"]


def test_save_multiple_records(chk_dir):
    """All records in the batch are persisted."""
    mgr = CheckpointManager(_cfg())
    records = [_record("r1", description_status="ok"), _record("r2"), _record("r3", description_status="ok")]
    run_key = make_run_key(records)
    mgr.save("repo", run_key, records)

    saved = mgr.load("repo", run_key)
    assert set(saved.keys()) == {"r1", "r2", "r3"}


def test_save_is_disabled_when_config_disabled(chk_dir):
    """No file is written when checkpoint is disabled."""
    mgr = CheckpointManager(_cfg(enabled=False))
    r = _record("r1", description_status="ok")
    mgr.save("repo", make_run_key([r]), [r])
    assert not any(chk_dir.iterdir())


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

def test_clear_removes_checkpoint_file(chk_dir):
    mgr = CheckpointManager(_cfg())
    r = _record("r1", description_status="ok")
    run_key = make_run_key([r])
    mgr.save("repo", run_key, [r])
    assert mgr.load("repo", run_key) != {}

    mgr.clear("repo", run_key)
    assert mgr.load("repo", run_key) == {}


def test_clear_is_idempotent(chk_dir):
    """Calling clear on a non-existent file must not raise."""
    CheckpointManager(_cfg()).clear("repo", "nonexistent")


def test_clear_is_disabled_when_config_disabled(chk_dir):
    """Disabled checkpoint must not delete files (even if they exist)."""
    path = chk_dir / "repo_aabbccddeeff.json"
    path.write_text("{}")
    CheckpointManager(_cfg(enabled=False)).clear("repo", "aabbccddeeff")
    assert path.exists()


# ---------------------------------------------------------------------------
# Atomic write safety
# ---------------------------------------------------------------------------

def test_no_stale_tmp_file_after_save(chk_dir):
    """Saving must not leave a .tmp file on disk."""
    mgr = CheckpointManager(_cfg())
    r = _record("r1")
    mgr.save("repo", make_run_key([r]), [r])
    assert not list(chk_dir.glob("*.tmp"))


# ---------------------------------------------------------------------------
# Repo name sanitisation
# ---------------------------------------------------------------------------

def test_repo_name_with_spaces(chk_dir):
    """Repo names with spaces produce valid file paths."""
    mgr = CheckpointManager(_cfg())
    r = _record("r1", description_status="ok")
    run_key = make_run_key([r])
    mgr.save("my repo name", run_key, [r])

    files = list(chk_dir.iterdir())
    assert len(files) == 1
    assert " " not in files[0].name
    assert "r1" in mgr.load("my repo name", run_key)
