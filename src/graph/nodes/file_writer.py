"""File writer node."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from src.core.runtime_paths import FAILED_PATCHES_DIR, ensure_runtime_dirs
from src.graph.nodes.support import require_state_value, strip_code_fences
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.tools.files import write_file
from src.tools.patches import apply_unified


logger = logging.getLogger(__name__)


async def file_writer_node(state: GraphState, run_context: RunContext) -> dict:
    start = time.time()
    try:
        target_file = require_state_value(state, "target_file")
        generated_code = strip_code_fences(require_state_value(state, "generated_code"))
        if state.get("generated_diff"):
            try:
                apply_unified(target_file, require_state_value(state, "generated_diff"))
            except Exception as exc:
                ensure_runtime_dirs()
                failed_path = FAILED_PATCHES_DIR / (Path(target_file).name + ".failed.patch")
                try:
                    failed_path.write_text(require_state_value(state, "generated_diff"), encoding="utf-8")
                except Exception as wexc:
                    logger.error("Failed to write failed patch file: %s", wexc)

                logger.error("Applying unified diff failed for %s: %s; saved to %s", target_file, exc, failed_path)

                emit_failure(run_context, "file_writer_node", state.get("task", ""), str(exc), start)

                return {
                    "verification_passed": False,
                    "verification_feedback": f"Applying unified diff failed: {exc}; saved failed patch at {failed_path}",
                }
        else:
            try:
                write_file(target_file, generated_code)
            except Exception as exc:
                ensure_runtime_dirs()
                failed_path = FAILED_PATCHES_DIR / (Path(target_file).name + ".failed.py")
                try:
                    failed_path.write_text(generated_code, encoding="utf-8")
                except Exception as wexc:
                    logger.error("Failed to write failed generated file: %s", wexc)

                logger.error("Writing file failed for %s: %s; saved to %s", target_file, exc, failed_path)
                emit_failure(run_context, "file_writer_node", state.get("task", ""), str(exc), start)

                return {
                    "verification_passed": False,
                    "verification_feedback": f"Writing file failed: {exc}; saved generated output at {failed_path}",
                }

        emit_success(run_context, "file_writer_node", state.get("task", ""), {"updated_length": len(generated_code)}, start)

        return {"updated_code": generated_code}
    except Exception as e:
        emit_failure(run_context, "file_writer_node", state.get("task", ""), str(e), start)
        raise
