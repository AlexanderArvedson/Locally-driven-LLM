"""Minimal JSONL logger for per-run observability events.

Provides one simple function `log_event(run_id, event)` which appends the
given event (a JSON-serializable dict) to `.runtime/runs/<run_id>.jsonl`.

This module intentionally keeps behavior synchronous and minimal: no
buffering, no external dependencies, and automatic directory creation.
"""

import json
from pathlib import Path

from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs


def log_event(run_id: str, event: dict) -> None:
    """Append `event` as one JSON line to the per-run JSONL file.

    Writes directly into the canonical `.runtime/runs/` directory so CI and
    local development use the same artifact layout.
    """
    ensure_runtime_dirs()

    path = RUNS_DIR / f"{run_id}.jsonl"
    # Ensure parent exists (ensure_runtime_dirs should have created it, but be defensive)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
