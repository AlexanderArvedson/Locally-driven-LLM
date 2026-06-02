"""File writer node."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from src.config_loader import get_repository_config, update_repository_timestamps
from src.core.runtime_paths import FAILED_PATCHES_DIR, ensure_runtime_dirs
from src.graph.nodes.support import require_state_value, strip_code_fences
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.tools.files import write_file
from src.tools.patches import apply_unified


logger = logging.getLogger(__name__)


async def file_writer_node(state: GraphState, run_context: RunContext) -> dict:
    """Write generated content to disk or apply a unified diff.

    Expected state input keys:
    - `target_file`: path to update
    - `generated_code`: full file text (used if `generated_diff` absent)
    - `generated_diff` (optional): unified diff to apply instead of overwriting

    Returns a dict with:
    - `updated_code`: the content written (str) on success
    On failure, returns verification keys describing the failure.
    """
    start = time.time()
    try:
        target_file = require_state_value(state, "target_file")
        generated_code = strip_code_fences(require_state_value(state, "generated_code"))
        if state.get("generated_diff"):
            try:
                apply_unified(target_file, require_state_value(state, "generated_diff"))
            except Exception as patch_exc:
                # Diff failed to apply — save the bad patch for inspection and
                # fall back to writing generated_code in full. This avoids
                # burning a retry cycle when the full content is already correct.
                ensure_runtime_dirs()
                failed_path = FAILED_PATCHES_DIR / (Path(target_file).name + ".failed.patch")
                try:
                    failed_path.write_text(require_state_value(state, "generated_diff"), encoding="utf-8")
                except Exception as wexc:
                    logger.error("Failed to save failed patch: %s", wexc)

                logger.warning(
                    "Unified diff failed for %s (%s); falling back to whole-file write. Patch saved at %s",
                    target_file, patch_exc, failed_path,
                )

                try:
                    write_file(target_file, generated_code)
                except Exception as fallback_exc:
                    logger.error("Whole-file fallback also failed for %s: %s", target_file, fallback_exc)
                    emit_failure(run_context, "file_writer_node", str(fallback_exc), start)
                    return {
                        "verification_passed": False,
                        "verification_feedback": (
                            f"Diff failed ({patch_exc}) and whole-file fallback also failed: {fallback_exc}"
                        ),
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
                emit_failure(run_context, "file_writer_node", str(exc), start)

                return {
                    "verification_passed": False,
                    "verification_feedback": f"Writing file failed: {exc}; saved generated output at {failed_path}",
                }

        emit_success(run_context, "file_writer_node", {"updated_length": len(generated_code)}, start)

        repo_path = state.get("repo_path")
        if repo_path:
            try:
                repo_config = get_repository_config(repo_path)
                update_repository_timestamps(
                    repo_config.name,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as ts_exc:
                logger.warning("Could not update updated_at timestamp: %s", ts_exc)

        return {"updated_code": generated_code}
    except Exception as e:
        emit_failure(run_context, "file_writer_node", str(e), start)
        raise
