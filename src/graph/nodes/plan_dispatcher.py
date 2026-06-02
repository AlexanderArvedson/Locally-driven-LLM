"""Plan dispatcher node — manages iteration over a multi-file execution plan.

Called once before each file edit: sets target_file to the next planned step,
resets all per-file validation state, refreshes related_file_contents for
already-written files so the coder sees up-to-date versions, and records the
active step details for the coder prompt.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from src.graph.nodes.support import require_state_value
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success

logger = logging.getLogger(__name__)

# Per-file state fields that must be reset before each new file is processed.
_PER_FILE_RESET: dict[str, object] = {
    "iteration": 0,
    "review_passed": None,
    "verification_passed": None,
    "semantic_passed": None,
    "original_code": None,
    "generated_code": None,
    "updated_code": None,
    "generated_diff": None,
    "review_feedback": None,
    "review_errors": None,
    "verification_feedback": None,
    "semantic_feedback": None,
    "runtime_ok": None,
    "error_type": None,
    "verifier_stderr": None,
    "verifier_stdout": None,
    "missing_requirements": None,
    "incorrect_behaviors": None,
    "unnecessary_changes": None,
    "semantic_notes": None,
    "semantic_confidence": None,
    "task_alignment_score": None,
    "regression_risk": None,
}

# Per-file character cap for related file contents shown to the coder.
_MAX_RELATED_FILE_CHARS = 2000

# Total character budget across ALL related file entries in a multi-file plan.
# Prevents context overflow when several files accumulate across plan steps.
# (Retrieval populates up to 5 files × 3 000 chars = 15 000 chars; that alone
# can push a 4 096-token context window to its limit before adding the target
# file's own content and the plan/task sections.)
_MAX_TOTAL_RELATED_CHARS = 8000


async def plan_dispatcher_node(state: GraphState, run_context: RunContext) -> dict:
    """Advance to the next step in the execution plan.

    State inputs consumed:
      change_plan, current_plan_step, modified_files, related_file_contents

    State delta returned:
      target_file, active_plan_step, current_plan_step (incremented),
      is_intermediate_step, per-file reset fields,
      related_file_contents (refreshed for already-modified files)
    """
    start = time.time()
    try:
        change_plan: list[dict] = require_state_value(state, "change_plan")
        current_step: int = state.get("current_plan_step", 0)

        if current_step >= len(change_plan):
            error = (
                f"plan_dispatcher: current_plan_step={current_step} is out of range "
                f"for plan of length {len(change_plan)}."
            )
            emit_failure(run_context, "plan_dispatcher_node", error, start)
            raise IndexError(error)

        step = change_plan[current_step]
        target_file: str = step["file"]
        next_step = current_step + 1
        is_intermediate = next_step < len(change_plan)

        # Build related_file_contents for the next coder step.
        #
        # Priority order (highest to lowest):
        #   1. Already-modified plan files — re-read from disk so the coder sees
        #      the updated versions and can maintain cross-file consistency.
        #   2. Retrieval-populated context files — kept only if budget allows.
        #
        # The total character budget prevents context overflow: in a multi-step
        # plan the dict would otherwise grow unboundedly (retrieval files carry
        # over from retrieval_node plus one new entry per completed step).
        modified_files: list[str] = state.get("modified_files") or []

        # Slot 1: already-written plan files (freshest, highest priority).
        plan_entries: dict[str, str] = {}
        for written_path in modified_files:
            try:
                content = Path(written_path).read_text(encoding="utf-8")
                plan_entries[written_path] = content[:_MAX_RELATED_FILE_CHARS]
            except OSError as read_err:
                logger.warning("plan_dispatcher: could not refresh %s: %s", written_path, read_err)

        # Slot 2: retrieval context files that still fit within the total budget.
        existing_related = state.get("related_file_contents") or {}
        remaining_budget = _MAX_TOTAL_RELATED_CHARS - sum(len(v) for v in plan_entries.values())
        retrieval_entries: dict[str, str] = {}
        for path, content in existing_related.items():
            if path in plan_entries:
                continue  # already included with fresh content
            if path == target_file:
                continue  # skip the file we're about to edit (file_reader will load it)
            chunk = content[:_MAX_RELATED_FILE_CHARS]
            if remaining_budget <= 0:
                break
            retrieval_entries[path] = chunk[:remaining_budget]
            remaining_budget -= len(retrieval_entries[path])

        related = {**retrieval_entries, **plan_entries}  # plan files win on key collision

        updates: dict = {
            "target_file": target_file,
            "active_plan_step": step,
            "current_plan_step": next_step,
            "is_intermediate_step": is_intermediate,
            "related_file_contents": related,
        }
        updates.update(_PER_FILE_RESET)

        emit_success(
            run_context,
            "plan_dispatcher_node",
            {
                "step_index": current_step,
                "file": target_file,
                "is_intermediate": is_intermediate,
            },
            start,
        )
        return updates
    except Exception as exc:
        emit_failure(run_context, "plan_dispatcher_node", str(exc), start)
        raise
