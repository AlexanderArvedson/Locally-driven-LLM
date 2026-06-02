"""Dependency analyzer node — expands planner's file selection to all affected files.

Uses the graphify knowledge graph for symbol-level matching and AstIndexer's
directed dependency edges for reverse-importer lookup. No LLM is involved;
this node is entirely graph-driven.

A file is considered "affected" if it is in the planner's initial selection OR
if it imports (directly or transitively, up to depth 2) from one of those files.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path

from src.graph.nodes.support import require_state_value
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.graph.graph_query import GraphQuery
from src.retrieval.indexing.ast_indexer import AstIndexer

logger = logging.getLogger(__name__)

_IMPORTER_BFS_DEPTH = 2


async def dependency_analyzer_node(state: GraphState, run_context: RunContext) -> dict:
    """Expand target_files to all files that may need modification.

    State inputs consumed:
      task, target_files, graph_path, repo_path, repo_sha

    State delta returned:
      affected_files   — ordered list of absolute paths (definitions first, importers after)
      plan_scope       — "single_file" | "multi_file"
      planner_error    — set when the graph is unavailable and analysis cannot proceed
    """
    start = time.time()
    try:
        repo_path = require_state_value(state, "repo_path")
        target_files: list[str] = state.get("target_files") or []
        task: str = state.get("task", "")
        graph_path: str | None = state.get("graph_path")
        repo_sha: str = state.get("repo_sha", "")

        if not target_files:
            error = "dependency_analyzer: no target_files to analyze."
            emit_failure(run_context, "dependency_analyzer_node", error, start)
            return {"planner_error": error}

        # Build the directed reverse-importer index from AST edges.
        importers_of = _build_importer_index(repo_path)

        # Expand each target file to include its importers (files that import from it).
        affected = _expand_with_importers(target_files, importers_of, depth=_IMPORTER_BFS_DEPTH)

        # Optionally enrich with graphify symbol-level matches so that if the task
        # mentions a symbol whose definition is in a file not yet in target_files,
        # we pull it in.
        if graph_path:
            try:
                gq = GraphQuery.from_path(Path(graph_path), repo_sha)
                task_kw = GraphQuery.task_words(task)
                if task_kw:
                    scored = gq.query_by_keywords(task_kw, top_k=10)
                    symbol_files = gq.files_for_scored_nodes(scored, repo_path)
                    for abs_path in symbol_files:
                        if abs_path not in affected and Path(abs_path).is_file():
                            affected.append(abs_path)
                            # Also expand importers of these newly added files.
                            extra = _expand_with_importers([abs_path], importers_of, depth=1)
                            for ep in extra:
                                if ep not in affected:
                                    affected.append(ep)
            except Exception as graph_exc:
                logger.warning("dependency_analyzer: graph query failed (continuing): %s", graph_exc)

        # Filter to only existing files.
        affected = [p for p in affected if Path(p).is_file()]

        scope = "multi_file" if len(affected) > 1 else "single_file"

        emit_success(
            run_context,
            "dependency_analyzer_node",
            {"scope": scope, "affected_count": len(affected)},
            start,
        )
        return {
            "affected_files": affected,
            "plan_scope": scope,
        }
    except Exception as exc:
        emit_failure(run_context, "dependency_analyzer_node", str(exc), start)
        raise


def _build_importer_index(repo_path: str) -> dict[str, list[str]]:
    """Return a mapping from each file to the list of files that import it."""
    indexer = AstIndexer()
    snapshot = indexer.build_snapshot(repo_path)
    importers_of: dict[str, list[str]] = defaultdict(list)
    for edge in snapshot.edges:
        importers_of[edge.to_path].append(edge.from_path)
    return dict(importers_of)


def _expand_with_importers(
    seed_files: list[str],
    importers_of: dict[str, list[str]],
    depth: int,
) -> list[str]:
    """BFS expansion: return seed_files plus all files that import from them.

    Preserves insertion order (seeds first, then importers breadth-first).
    """
    visited: set[str] = set(seed_files)
    result: list[str] = list(seed_files)
    queue: deque[tuple[str, int]] = deque((f, 0) for f in seed_files)

    while queue:
        current, d = queue.popleft()
        if d >= depth:
            continue
        for importer in importers_of.get(current, []):
            if importer not in visited:
                visited.add(importer)
                result.append(importer)
                queue.append((importer, d + 1))

    return result
