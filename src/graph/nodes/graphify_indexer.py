"""Graphify indexer node — builds a knowledge graph of the target repository.

Runs AST extraction on `repo_path` and saves the result to
`{graph_path}/graph.json`. On subsequent runs the graph is reused if it was
built within the last hour; otherwise it is rebuilt (graphify's file-level
cache makes repeat runs fast for unchanged files).
"""

from __future__ import annotations

import time
from pathlib import Path

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success

_STALE_SECONDS = 3600


async def graphify_indexer_node(state: GraphState, run_context: RunContext) -> dict:
    """Build or refresh the graphify knowledge graph for the target repository.

    Reads `repo_path` and `graph_path` from state. The graph is written to
    `{graph_path}/graph.json` so it stays out of the target repo. Returns an
    empty dict — this node exists for its disk side-effect only.
    """
    start = time.time()
    task = state.get("task", "")
    try:
        repo_path = state.get("repo_path")
        graph_path = state.get("graph_path")

        if not repo_path or not graph_path:
            emit_success(run_context, "graphify_indexer_node", task, {"skipped": True}, start)
            return {}

        graph_dir = Path(graph_path)
        graph_json = graph_dir / "graph.json"

        if graph_json.exists():
            age = time.time() - graph_json.stat().st_mtime
            if age < _STALE_SECONDS:
                emit_success(run_context, "graphify_indexer_node", task, {"cached": True, "age_s": int(age)}, start)
                return {}

        graph_dir.mkdir(parents=True, exist_ok=True)
        _build_ast_graph(repo_path, graph_dir)

        emit_success(run_context, "graphify_indexer_node", task, {"graph_path": str(graph_json)}, start)
        return {}
    except Exception as e:
        emit_failure(run_context, "graphify_indexer_node", task, str(e), start)
        raise


def _build_ast_graph(repo_path: str, graph_dir: Path) -> None:
    """Run AST-only graphify extraction and write graph.json to graph_dir."""
    from graphify.detect import detect
    from graphify.extract import collect_files, extract
    from graphify.build import build_from_json
    from graphify.cluster import cluster
    from graphify.export import to_json

    detected = detect(Path(repo_path))
    code_files: list[Path] = []
    for f in detected.get("files", {}).get("code", []):
        p = Path(f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])

    if not code_files:
        return

    # cache_root=graph_dir keeps all graphify cache files out of the target repo
    extraction = extract(code_files, cache_root=graph_dir)
    G = build_from_json(extraction)
    if G.number_of_nodes() == 0:
        return

    communities = cluster(G)
    to_json(G, communities, str(graph_dir / "graph.json"))
