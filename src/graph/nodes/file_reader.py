"""File reader node."""

from __future__ import annotations

import logging
import time

from src.graph.nodes.support import require_state_value, select_target_file_from_repo_path
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.slicing import SymbolSlice, get_slicer
from src.tools.files import read_file

logger = logging.getLogger(__name__)


async def file_reader_node(state: GraphState, run_context: RunContext) -> dict:
    """Read the target file and, when a target symbol is set, build a context slice.

    Returns:
      original_code  — full file content (used by diff_generator and file_writer)
      target_file    — resolved absolute path
      context_slice  — symbol-level context dict, or None when slicing is skipped
    """
    start = time.time()
    try:
        target_file = state.get("target_file")
        if not target_file:
            repo_path = require_state_value(state, "repo_path")
            target_file = select_target_file_from_repo_path(repo_path)

        original = read_file(target_file)
        result: dict = {"original_code": original, "target_file": target_file}

        target_symbol = (state.get("target_symbol") or "").strip()
        if target_symbol:
            slicer = get_slicer(target_file)
            if slicer is not None:
                ctx = _build_context_slice(slicer, original, target_symbol, target_file)
                result["context_slice"] = ctx
                slice_ok = ctx.get("target_source") is not None
            else:
                result["context_slice"] = None
                slice_ok = False
                logger.debug("file_reader: no slicer for %s; falling back to full-file", target_file)
        else:
            result["context_slice"] = None
            slice_ok = False

        emit_success(
            run_context,
            "file_reader_node",
            {
                "original_length": len(original),
                "target_file": target_file,
                "symbol": target_symbol or None,
                "slice_built": slice_ok,
            },
            start,
        )
        return result
    except Exception as e:
        emit_failure(run_context, "file_reader_node", str(e), start)
        raise


def _build_context_slice(slicer, source: str, symbol_name: str, target_file: str) -> dict:
    """Assemble the context dict for the coder's focused prompt."""
    sl: SymbolSlice | None = slicer.extract_symbol(source, symbol_name)

    return {
        "target_symbol": symbol_name,
        "target_source": sl.source if sl else None,
        "symbol_start_line": sl.start_line if sl else None,
        "symbol_end_line": sl.end_line if sl else None,
        "symbol_indent": sl.indent if sl else 0,
        "required_imports": slicer.extract_imports_for(source, symbol_name) if sl else "",
        "class_context": slicer.extract_class_context(source, symbol_name) if sl else None,
        "contracts": slicer.extract_contracts(source, symbol_name) if sl else "",
    }
