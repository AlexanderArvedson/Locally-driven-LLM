"""Reviewer node."""

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


async def reviewer_node(state: GraphState, run_context: RunContext) -> dict:
    """Perform lightweight review checks on generated code.

    Performs the following checks in order:
    - Basic Python syntax validation via `validate_python_syntax`.
    - If `ruff` is available on PATH, run `ruff check` on a temporary file
      and treat any non-zero exit as a failure.
    - Apply simple heuristics (presence of `def `, absence of `TODO`, length).

    The function returns a dict with `review_passed` (bool) and
    `review_feedback` (str). Linter usage is optional and depends on the
    runtime environment; callers should not assume `ruff` is available.
    """
    start = time.time()
    try:
        code = strip_code_fences(require_state_value(state, "generated_code"))
        passed, feedback = validate_python_syntax(code)

        if not passed:
            emit_failure(run_context, "reviewer_node", feedback, start)
            return {"review_passed": False, "review_feedback": feedback}

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
                    out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
                    emit_failure(run_context, "reviewer_node", out, start)
                    return {"review_passed": False, "review_feedback": f"Ruff reported issues:\n{out}"}
            except FileNotFoundError:
                pass
            finally:
                try:
                    if tf_name is not None and Path(tf_name).exists():
                        Path(tf_name).unlink()
                except Exception:
                    pass

        heur_pass = (
            "def " in code
            and "TODO" not in code
            and len(code) > 20
        )
        if not heur_pass:
            emit_failure(run_context, "reviewer_node", "Heuristic checks failed", start)
            return {"review_passed": False, "review_feedback": "Heuristic checks failed: ensure function definitions exist, avoid TODO markers, and file is non-trivial."}

        emit_success(run_context, "reviewer_node", {"review_passed": True}, start)

        return {"review_passed": True, "review_feedback": ""}
    except Exception as e:
        emit_failure(run_context, "reviewer_node", str(e), start)
        raise
