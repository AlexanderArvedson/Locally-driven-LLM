"""Diff generator node."""

from __future__ import annotations

import time

from src.graph.nodes.support import require_state_value, strip_code_fences
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.tools.patches import generate_unified


async def diff_generator_node(state: GraphState, run_context: RunContext) -> dict:
    """Compute a unified diff between the original and generated code.

    Expected state input keys:
    - `original_code`: the original file contents (str)
    - `generated_code`: the generated file contents (str)
    - `target_file` (optional): used to populate diff file names

    Returns a dict with:
    - `generated_diff`: unified diff string
    """
    start = time.time()
    try:
        original = require_state_value(state, "original_code")
        generated = strip_code_fences(require_state_value(state, "generated_code"))
        nd = generate_unified(original, generated, fromfile=str(state.get("target_file", "a")), tofile=str(state.get("target_file", "b")))

        emit_success(run_context, "diff_generator_node", {"diff_length": len(nd)}, start)

        return {"generated_diff": nd}
    except Exception as e:
        emit_failure(run_context, "diff_generator_node", str(e), start)
        raise
