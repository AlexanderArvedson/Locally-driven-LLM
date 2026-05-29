"""Small helper utilities for observability event emission.

Provides helpers to emit success/failure events with consistent compact shape
and duration calculation. Events no longer carry `run_id` or `task` per-line;
those fields live once on `RunContext` and are written to the top-level run
summary by `write_run_summary` in logger.py.

Each emitted event is both appended to `run_context.events` (in-memory, for the
final summary) and written as a JSONL line (for streaming/crash durability).
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict

from .logger import log_event
from .context import RunContext


ALLOWED_TOP_LEVEL_KEYS = {"node", "status", "duration_ms", "timestamp", "payload"}


def emit_event(run_context: RunContext,
               node: str,
               status: str,
               payload: Dict[str, Any],
               start_time: float | None = None) -> None:
    """Emit a single compact observability event.

    Args:
        run_context: The RunContext for this run (provides run_id for JSONL routing).
        node: Logical node name.
        status: Either "success" or "failure".
        payload: Node-specific payload dictionary.
        start_time: Optional start time from `time.time()` to calculate duration_ms.
    """
    duration_ms = int((time.time() - start_time) * 1000) if start_time is not None else 0

    event = {
        "node": node,
        "status": status,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }

    # Prune any accidental extra keys to keep the contract stable
    extra_keys = set(event.keys()) - ALLOWED_TOP_LEVEL_KEYS
    for k in extra_keys:
        event.pop(k, None)

    run_context.events.append(event)
    log_event(run_context.run_id, event)


def emit_success(run_context: RunContext, node: str, payload: Dict[str, Any] | None = None, start_time: float | None = None) -> None:
    """Emit a success event for the given node."""
    emit_event(run_context, node, "success", payload or {}, start_time)


def emit_failure(run_context: RunContext, node: str, error: str, start_time: float | None = None) -> None:
    """Emit a failure event for the given node with the error message in the payload."""
    emit_event(run_context, node, "failure", {"error": error}, start_time)
