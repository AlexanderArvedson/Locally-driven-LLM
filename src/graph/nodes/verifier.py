"""Verifier node."""

from __future__ import annotations

import time

from src.graph.nodes.support import require_state_value, strip_code_fences, validate_python_syntax
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
import os
from src.tools.sandbox import run_code_in_sandbox


async def verifier_node(state: GraphState, run_context: RunContext) -> dict:
    """Verify generated code by performing static checks and (optionally) sandboxed execution.

    By default this node performs static syntax validation and then either
    executes the code in a subprocess sandbox (if `VERIFIER_USE_SUBPROCESS`
    environment variable is truthy) or falls back to in-process `exec`.

    Returns a dict with `verification_passed` (bool) and
    `verification_feedback` (str).
    """
    start = time.time()
    try:
        code = strip_code_fences(require_state_value(state, "generated_code"))

        passed, feedback = validate_python_syntax(code)
        if not passed:
            emit_failure(run_context, "verifier_node", state.get("task", ""), feedback, start)
            return {"verification_passed": False, "verification_feedback": feedback}

        # Prefer sandboxed subprocess execution when explicitly enabled.
        use_subproc = os.getenv("VERIFIER_USE_SUBPROCESS", "false").lower() in ("1", "true", "yes")
        if use_subproc:
            try:
                rc, out, err = run_code_in_sandbox(code, timeout=10, memory_mb=200, cpu_seconds=5)
            except Exception as exc:
                emit_failure(run_context, "verifier_node", state.get("task", ""), str(exc), start)
                return {"verification_passed": False, "verification_feedback": f"Sandbox error: {exc}"}

            if rc != 0:
                feedback = (err or out or f"subprocess exited with code {rc}").strip()
                emit_failure(run_context, "verifier_node", state.get("task", ""), feedback, start)
                return {"verification_passed": False, "verification_feedback": feedback}
        else:
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
