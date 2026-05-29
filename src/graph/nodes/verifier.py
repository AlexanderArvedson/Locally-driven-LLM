"""Verifier node."""

from __future__ import annotations

import os
import time

from src.graph.nodes.support import require_state_value, strip_code_fences, validate_python_syntax
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.tools.sandbox import run_code_in_sandbox


def _classify_error(stderr: str | None, stdout: str | None) -> str:
    """Return a coarse error category from subprocess output."""
    combined = (stderr or "") + (stdout or "")
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        return "ImportError"
    if "SyntaxError" in combined:
        return "SyntaxError"
    return "RuntimeError"


async def verifier_node(state: GraphState, run_context: RunContext) -> dict:
    """Verify generated code by executing it in a sandboxed subprocess.

    Subprocess execution is the default. Set VERIFIER_USE_SUBPROCESS=false to
    fall back to in-process exec (useful in environments where subprocess is
    unavailable). Returns structured output capturing runtime_ok, error_type,
    stderr, and stdout independently so the coder node can build targeted
    failure feedback.
    """
    start = time.time()
    try:
        code = strip_code_fences(require_state_value(state, "generated_code"))

        passed, feedback = validate_python_syntax(code)
        if not passed:
            emit_failure(run_context, "verifier_node", feedback, start)
            return {
                "verification_passed": False,
                "verification_feedback": feedback,
                "runtime_ok": False,
                "error_type": "SyntaxError",
                "verifier_stderr": feedback,
                "verifier_stdout": None,
            }

        use_subproc = os.getenv("VERIFIER_USE_SUBPROCESS", "true").lower() not in ("0", "false", "no")

        if use_subproc:
            try:
                rc, out, err = run_code_in_sandbox(code, timeout=10, memory_mb=200, cpu_seconds=5)
            except Exception as exc:
                msg = f"Sandbox error: {exc}"
                emit_failure(run_context, "verifier_node", msg, start)
                return {
                    "verification_passed": False,
                    "verification_feedback": msg,
                    "runtime_ok": False,
                    "error_type": "RuntimeError",
                    "verifier_stderr": msg,
                    "verifier_stdout": None,
                }

            if rc != 0:
                error_feedback = (err or out or f"subprocess exited with code {rc}").strip()
                error_type = _classify_error(err, out)
                emit_failure(run_context, "verifier_node", error_feedback, start)
                return {
                    "verification_passed": False,
                    "verification_feedback": error_feedback,
                    "runtime_ok": False,
                    "error_type": error_type,
                    "verifier_stderr": err or None,
                    "verifier_stdout": out or None,
                }

            emit_success(run_context, "verifier_node", {"verification_passed": True}, start)
            return {
                "verification_passed": True,
                "verification_feedback": "",
                "runtime_ok": True,
                "error_type": None,
                "verifier_stderr": None,
                "verifier_stdout": out or None,
            }

        else:
            ns: dict = {}
            try:
                exec(code, ns)  # noqa: S102
            except Exception as exc:
                msg = f"Runtime exec error: {exc}"
                emit_failure(run_context, "verifier_node", msg, start)
                return {
                    "verification_passed": False,
                    "verification_feedback": msg,
                    "runtime_ok": False,
                    "error_type": type(exc).__name__,
                    "verifier_stderr": msg,
                    "verifier_stdout": None,
                }

            emit_success(run_context, "verifier_node", {"verification_passed": True}, start)
            return {
                "verification_passed": True,
                "verification_feedback": "",
                "runtime_ok": True,
                "error_type": None,
                "verifier_stderr": None,
                "verifier_stdout": None,
            }

    except Exception as e:
        emit_failure(run_context, "verifier_node", str(e), start)
        raise
