"""File reader node."""

from __future__ import annotations

import time

from src.graph.nodes.support import require_state_value, select_target_file_from_repo_path
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.tools.files import read_file


async def file_reader_node(state: GraphState, run_context: RunContext) -> dict:
    start = time.time()
    try:
        target_file = state.get("target_file")
        if not target_file:
            repo_path = require_state_value(state, "repo_path")
            target_file = select_target_file_from_repo_path(repo_path)

        original = read_file(target_file)

        emit_success(run_context, "file_reader_node", state.get("task", ""), {"original_length": len(original), "target_file": target_file}, start)

        return {"original_code": original, "target_file": target_file}
    except Exception as e:
        emit_failure(run_context, "file_reader_node", state.get("task", ""), str(e), start)
        raise
