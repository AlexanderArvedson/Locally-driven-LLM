"""Small helper utilities for observability event emission.

Provides helpers to emit success/failure events with consistent shape and
duration calculation to reduce duplication across node implementations.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict

from .logger import log_event
from .context import RunContext


ALLOWED_TOP_LEVEL_KEYS = {"run_id", "node", "status", "duration_ms", "task", "timestamp", "payload"}


def emit_event(run_context: RunContext, 
               node: str, 
               status: str, 
               task: str, 
               payload: Dict[str, Any], 
               start_time: float 
               | None = None) -> None:
    """Emit a single observability event with consistent shape.

    Args:
        run_context: The RunContext for this run.
        node: Logical node name.
        status: Either "success" or "failure".
        task: The task description from state.
        payload: Node-specific payload dictionary.
        start_time: Optional start time (as returned by `time.time()`) to calculate duration_ms.
    """
    duration_ms = 0
    if start_time is not None:
        duration_ms = int((time.time() - start_time) * 1000)

    event = {
        "run_id": run_context.run_id,
        "node": node,
        "status": status,
        "duration_ms": duration_ms,
        "task": task,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }

    # Ensure event has only the allowed top-level keys
    # (keeps the contract stable and prevents accidental leakage)
    extra_keys = set(event.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if extra_keys:
        # prune any accidental extras (defensive; we also keep payload intact)
        for k in extra_keys:
            event.pop(k, None)

    log_event(run_context.run_id, event)


def emit_success(run_context: RunContext, node: str, task: str, payload: Dict[str, Any] | None = None, start_time: float | None = None) -> None:
    emit_event(run_context, node, "success", task, payload or {}, start_time)


def emit_failure(run_context: RunContext, node: str, task: str, error: str, start_time: float | None = None) -> None:
    emit_event(run_context, node, "failure", task, {"error": error}, start_time)
