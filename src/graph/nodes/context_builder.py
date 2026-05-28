"""Repository context builder node."""

from __future__ import annotations

import time
from pathlib import Path

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.repository.context_builder import SimpleContextBuilder
from src.repository.context_contract import build_repository_context_payload
from src.repository.retrieval_engine import SimpleRetrievalEngine
from src.repository.simple_repository_indexer import SimpleRepositoryIndexer


async def context_builder_node(state: GraphState, run_context: RunContext) -> dict:
    """Build repository context for the current task and target file.

    Expected state input keys:
    - `task`: human-readable task instruction (str)
    - `target_file` or `repo_path`: where to derive repository snapshot

    On success, stores `repository_snapshot` and `repository_context` in
    `state` and returns a dict with `repository_context` payload.
    """
    start = time.time()
    task = state.get("task", "")
    try:
        target_file = state.get("target_file")
        repo_path = state.get("repo_path")

        snapshot = state.get("repository_snapshot")
        if snapshot is None:
            indexer = SimpleRepositoryIndexer()
            snapshot_root = repo_path or (str(Path(target_file).parent) if target_file else ".")
            snapshot = indexer.build_snapshot(snapshot_root)
            state["repository_snapshot"] = snapshot

        retriever = SimpleRetrievalEngine()
        selected = retriever.select_files(task, snapshot, target_file=target_file, max_files=15)

        builder = SimpleContextBuilder()
        context_pkg = builder.build_context(task, target_file, selected, snapshot, max_files=15)

        serialized = build_repository_context_payload(context_pkg, selected, repo_path=repo_path)
        state["repository_context"] = serialized

        payload = {
            "selected_files": selected,
            "num_selected": len(selected),
            "total_symbols": context_pkg.total_symbols,
        }
        emit_success(run_context, "context_builder_node", task, payload, start)

        return {"repository_context": serialized}
    except Exception as e:
        emit_failure(run_context, "context_builder_node", task, str(e), start)
        raise
