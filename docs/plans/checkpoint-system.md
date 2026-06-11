# Plan: Pipeline Checkpoint System

## Goal

Persist in-progress pipeline state to disk so a crash during the expensive
description-generation (or embedding) stage can be resumed from the last
saved point rather than restarting from scratch.

---

## Config change — `contracts.py`

Add a new frozen dataclass and wire it into `PipelineConfig`:

```python
@dataclass(frozen=True)
class CheckpointConfig:
    enabled: bool = True
    interval: int = 10          # save after every N completed descriptions
    directory: str = ".pipeline_checkpoints"
```

Add `checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)`
to `PipelineConfig`.

---

## New module — `src/pipeline/checkpoint.py`

A `CheckpointManager` class with three public methods:

| Method | Responsibility |
|--------|---------------|
| `load(run_key)` | Read checkpoint file; return saved records dict or `{}` if missing/stale |
| `save(run_key, records)` | Serialise relevant fields of all records to JSON on disk |
| `clear(run_key)` | Delete the checkpoint file on successful pipeline completion |

**Run key** — `sha256` of the sorted list of changed record IDs. This means
a checkpoint is automatically stale (and ignored) if the changed-set shifts
between runs (e.g. new commits landed).

**Saved fields per record** — only what's expensive to regenerate:
`description`, `description_status`, `code_embedding`,
`code_embedding_status`, `description_embedding`.

**File path** — `{directory}/{repo_name}_{run_key[:12]}.json`.

---

## Integration — `pipeline.py`

### On startup (after partitioning `changed`/`unchanged`)
1. Instantiate `CheckpointManager(config.checkpoint)`.
2. Compute `run_key`.
3. Call `manager.load(run_key)` and pre-populate matching `changed` records
   in-place (skip records whose `description_status` is already `"ok"`).

### During description stage
Wrap the existing `_on_desc_progress` callback: every time `completed %
interval == 0`, call `manager.save(run_key, changed)`.

The same pattern applies to the code-embedding progress callback so an
early crash there is also covered, though it's much faster in practice.

### On success
Call `manager.clear(run_key)` at the end of `_run_stages` (after stage 12).

---

## Files touched

| File | Change |
|------|--------|
| `src/pipeline/contracts.py` | Add `CheckpointConfig`; add field to `PipelineConfig` |
| `src/pipeline/checkpoint.py` | New — `CheckpointManager` (~80 lines) |
| `src/pipeline/pipeline.py` | Load on start, save in progress callbacks, clear on success |
| `config.json` / docs | Expose `checkpoint.interval` and `checkpoint.directory` to users |
| `tests/pipeline/test_checkpoint.py` | New — unit tests for load/save/clear and stale-key behaviour |

---

## Out of scope

- Neo4j-side checkpointing (the existing hash-based skip already handles
  unchanged functions across full runs).
- Similarity-edge checkpointing (fast, not worth the complexity).
