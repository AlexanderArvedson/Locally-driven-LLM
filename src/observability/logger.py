"""Minimal JSONL logger for per-run observability events.

Provides one simple function `log_event(run_id, event)` which appends the
given event (a JSON-serializable dict) to `logs/runs/<run_id>.jsonl`.

This module intentionally keeps behavior synchronous and minimal: no
buffering, no external dependencies, and automatic directory creation.
"""

import json
from pathlib import Path


LOG_DIR = Path("logs/runs")


def log_event(run_id: str, event: dict) -> None:
    """Append `event` as one JSON line to the per-run JSONL file.

    Args:
        run_id: The UUID string for the current run.
        event: A JSON-serializable mapping describing the node event.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    path = LOG_DIR / f"{run_id}.jsonl"

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
