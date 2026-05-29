"""Retrieval node — orchestrates the graph-backed retrieval pipeline.

Pipeline stages (all internal; only lightweight references enter GraphState):
  1. AST indexing   — build RepositorySnapshot locally (never stored in state)
  2. Candidate retrieval — graph keyword query or heuristic fallback
  3. Semantic ranking    — graph-aware (GraphRanker) or heuristic (HeuristicRanker)
  4. Dependency expansion — one BFS hop via GraphQuery (graph path only)
  5. Context budgeting   — enforce file-count and char limits (ContextBudget)
  6. Context assembly    — build bounded ContextPackage (ContextAssembler)
  7. Return lightweight state delta (session ID, file IDs, SHA, payload)
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.assembly.context_assembler import ContextAssembler
from src.retrieval.budgeting.context_budget import ContextBudget
from src.retrieval.contracts.context_contract import build_repository_context_payload
from src.retrieval.graph.graph_query import GraphQuery
from src.retrieval.indexing.ast_indexer import AstIndexer
from src.retrieval.ranking.graph_ranker import GraphRanker
from src.retrieval.ranking.heuristic_ranker import HeuristicRanker
from src.tools.files import read_file


_MAX_RELATED_FILES = 5
_MAX_CHARS_PER_FILE = 3_000


async def retrieval_node(state: GraphState, run_context: RunContext) -> dict:
    """Build repository context for the current task and target file.

    Retrieval strategy:
    - When `graph_path` is set and a valid graph.json is present, uses
      GraphRanker (keyword match + BFS dependency expansion via GraphQuery).
    - Falls back to HeuristicRanker (import/directory/keyword heuristics) when
      the graph is unavailable.

    State inputs consumed:
      task, target_file, repo_path, graph_path, repo_sha (all optional except task)

    State delta returned (lightweight references only):
      retrieval_session_id, selected_file_ids, graph_snapshot_sha,
      repository_context, related_file_contents
    """
    start = time.time()
    task = state.get("task", "")
    try:
        target_file = state.get("target_file")
        repo_path = state.get("repo_path")
        graph_path = state.get("graph_path")
        repo_sha = state.get("repo_sha", "")

        # --- Stage 1: AST indexing (local; never stored in state) ---
        indexer = AstIndexer()
        if target_file and repo_path:
            snapshot_root = str(Path(target_file).parent)
        else:
            snapshot_root = repo_path or (str(Path(target_file).parent) if target_file else ".")
        snapshot = indexer.build_snapshot(snapshot_root)

        # --- Stages 2-4: candidate retrieval + ranking + dep expansion ---
        graph_json = Path(graph_path) / "graph.json" if graph_path else None
        used_graph = bool(graph_json and graph_json.exists())
        graph_snapshot_sha = ""

        if used_graph:
            try:
                graph_query = GraphQuery.from_path(Path(graph_path), repo_sha)
                graph_snapshot_sha = graph_query.graph_snapshot_sha
                ranker = GraphRanker()
                ranked = ranker.rank_candidates(
                    task,
                    graph_query,
                    repo_path or ".",
                    target_file=target_file,
                    max_files=20,  # rank wider, budget will trim
                )
            except (FileNotFoundError, Exception):
                # Graph unavailable at runtime — fall back gracefully.
                used_graph = False
                graph_snapshot_sha = ""
                ranked = _heuristic_rank(task, snapshot, target_file)
        else:
            ranked = _heuristic_rank(task, snapshot, target_file)

        # --- Stage 5: context budgeting ---
        budget = ContextBudget(max_files=15, max_chars_per_file=_MAX_CHARS_PER_FILE, max_total_chars=30_000)
        allocation = budget.allocate(ranked, target_file)
        selected = allocation.selected_files

        # --- Stage 6: context assembly ---
        assembler = ContextAssembler()
        context_pkg = assembler.build(task, target_file, selected, snapshot, max_files=15)
        payload = build_repository_context_payload(context_pkg, selected, repo_path=repo_path)

        # --- Stage 7: read bounded file contents for the coder prompt ---
        related_file_contents = _read_related_files(selected, target_file)

        # Lightweight selected_file_ids: normalised relative paths when possible.
        selected_file_ids = _to_relative_ids(selected, repo_path)
        session_id = str(uuid.uuid4())

        emit_success(
            run_context,
            "retrieval_node",
            {
                "session_id": session_id,
                "num_selected": len(selected),
                "files_dropped": allocation.files_dropped,
                "total_symbols": context_pkg.total_symbols,
                "used_graph": used_graph,
                "graph_snapshot_sha": graph_snapshot_sha[:8] if graph_snapshot_sha else "",
                "related_files_read": len(related_file_contents),
            },
            start,
        )
        return {
            "retrieval_session_id": session_id,
            "selected_file_ids": selected_file_ids,
            "graph_snapshot_sha": graph_snapshot_sha,
            "repository_context": payload,
            "related_file_contents": related_file_contents,
        }
    except Exception as e:
        emit_failure(run_context, "retrieval_node", str(e), start)
        raise


def _heuristic_rank(task: str, snapshot, target_file) -> list[str]:
    """Fallback ranking when graph is unavailable."""
    return HeuristicRanker().rank_candidates(task, snapshot, target_file=target_file, max_files=20)


def _read_related_files(selected: list[str], target_file: str | None) -> dict[str, str]:
    """Read bounded file contents for the coder prompt, excluding target file."""
    contents: dict[str, str] = {}
    for path in selected:
        if path == target_file:
            continue
        if len(contents) >= _MAX_RELATED_FILES:
            break
        try:
            text = read_file(path)
            if len(text) > _MAX_CHARS_PER_FILE:
                text = text[:_MAX_CHARS_PER_FILE] + f"\n... [truncated at {_MAX_CHARS_PER_FILE} chars]"
            contents[path] = text
        except OSError:
            continue
    return contents


def _to_relative_ids(selected: list[str], repo_path: str | None) -> list[str]:
    """Convert absolute paths to repo-relative strings when possible."""
    if not repo_path:
        return selected
    from pathlib import Path as _Path
    repo = _Path(repo_path)
    result = []
    for p in selected:
        try:
            result.append(str(_Path(p).relative_to(repo)))
        except ValueError:
            result.append(p)
    return result
