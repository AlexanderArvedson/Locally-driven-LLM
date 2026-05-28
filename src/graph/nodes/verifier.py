"""Verifier node."""

from __future__ import annotations

import time

from src.graph.nodes.support import require_state_value, strip_code_fences, validate_python_syntax
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success


async def verifier_node(state: GraphState, run_context: RunContext) -> dict:
    start = time.time()
    try:
        code = strip_code_fences(require_state_value(state, "generated_code"))

        passed, feedback = validate_python_syntax(code)
        if not passed:
            emit_failure(run_context, "verifier_node", state.get("task", ""), feedback, start)
            return {"verification_passed": False, "verification_feedback": feedback}

        ns: dict = {}
        try:
            exec(code, ns)
        except Exception as exc:
            emit_failure(run_context, "verifier_node", state.get("task", ""), str(exc), start)
            return {"verification_passed": False, "verification_feedback": f"Runtime exec error: {exc}"}

        emit_success(run_context, "verifier_node", state.get("task", ""), {"verification_passed": True}, start)

        return {"verification_passed": True, "verification_feedback": ""}
    except Exception as e:
        emit_failure(run_context, "verifier_node", state.get("task", ""), str(e), start)
        raise
