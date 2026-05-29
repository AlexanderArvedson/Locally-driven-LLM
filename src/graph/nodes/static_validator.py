"""Static validator node.

Replaces the former reviewer node. Responsibilities are strictly limited to
structural correctness: Python syntax validation and optional ruff linting.
No heuristic business logic (function presence, TODO markers, file length)
belongs here — those judgements are delegated to semantic_validator.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from src.graph.nodes.support import require_state_value, strip_code_fences, validate_python_syntax
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success


async def static_validator_node(state: GraphState, run_context: RunContext) -> dict:
    """Validate generated code for structural correctness.

    Runs Python syntax validation via compile() and, when ruff is available
    on PATH, a ruff check pass. Returns structured output describing each
    check independently so downstream nodes can distinguish syntax errors
    from lint violations.
    """
    start = time.time()
    try:
        code = strip_code_fences(require_state_value(state, "generated_code"))

        passed, syntax_error = validate_python_syntax(code)
        if not passed:
            emit_failure(run_context, "static_validator_node", syntax_error, start)
            return {
                "review_passed": False,
                "review_feedback": syntax_error,
                "syntax_ok": False,
                "lint_ok": False,
                "review_errors": [syntax_error],
            }

        if shutil.which("ruff"):
            tf = None
            tf_name = None
            try:
                tf = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
                tf.write(code)
                tf.flush()
                tf_name = tf.name
                tf.close()

                res = subprocess.run(["ruff", "check", tf_name], capture_output=True, text=True)
                if res.returncode != 0:
                    ruff_out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
                    ruff_out = ruff_out.strip()
                    emit_failure(run_context, "static_validator_node", ruff_out, start)
                    return {
                        "review_passed": False,
                        "review_feedback": f"Ruff reported issues:\n{ruff_out}",
                        "syntax_ok": True,
                        "lint_ok": False,
                        "review_errors": ruff_out.splitlines(),
                    }
            except FileNotFoundError:
                pass
            finally:
                try:
                    if tf_name is not None and Path(tf_name).exists():
                        Path(tf_name).unlink()
                except Exception:
                    pass

        emit_success(run_context, "static_validator_node", {"review_passed": True}, start)
        return {
            "review_passed": True,
            "review_feedback": "",
            "syntax_ok": True,
            "lint_ok": True,
            "review_errors": [],
        }

    except Exception as e:
        emit_failure(run_context, "static_validator_node", str(e), start)
        raise
