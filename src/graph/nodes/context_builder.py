"""Repository context builder node."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.repository.context_builder import SimpleContextBuilder
from src.repository.context_contract import build_repository_context_payload
from src.repository.retrieval_engine import SimpleRetrievalEngine
from src.repository.simple_repository_indexer import SimpleRepositoryIndexer
from src.tools.files import read_file

_STOPWORDS = {
    "the", "a", "an", "in", "of", "to", "for", "and", "or", "is", "it",
    "be", "this", "that", "with", "from", "by", "we", "i", "add", "use",
}


async def context_builder_node(state: GraphState, run_context: RunContext) -> dict:
    """Build repository context for the current task and target file.

    When `graph_path` is set in state and a graph.json exists there, uses the
    graphify knowledge graph to select relevant files by BFS over node labels
    matched against task keywords. Falls back to SimpleRetrievalEngine when
    the graph is unavailable.

    Expected state input keys:
    - `task`: human-readable task instruction (str)
    - `target_file` or `repo_path`: where to derive repository snapshot
    - `graph_path` (optional): path to the graphify-out directory for the repo
    """
    start = time.time()
    task = state.get("task", "")
    try:
        target_file = state.get("target_file")
        repo_path = state.get("repo_path")
        graph_path = state.get("graph_path")

        snapshot = state.get("repository_snapshot")
        if snapshot is None:
            indexer = SimpleRepositoryIndexer()
            if target_file and repo_path:
                # Use the target file's immediate parent so we only index the
                # relevant module/package, not the entire monorepo.
                snapshot_root = str(Path(target_file).parent)
            else:
                snapshot_root = repo_path or (str(Path(target_file).parent) if target_file else ".")
            snapshot = indexer.build_snapshot(snapshot_root)
            state["repository_snapshot"] = snapshot

        graph_json = Path(graph_path) / "graph.json" if graph_path else None
        used_graph = bool(graph_json and graph_json.exists())

        if used_graph:
            selected = _select_files_from_graph(
                task, graph_json, repo_path or ".", target_file, max_files=15
            )
        else:
            retriever = SimpleRetrievalEngine()
            selected = retriever.select_files(task, snapshot, target_file=target_file, max_files=15)

        builder = SimpleContextBuilder()
        context_pkg = builder.build_context(task, target_file, selected, snapshot, max_files=15)

        serialized = build_repository_context_payload(context_pkg, selected, repo_path=repo_path)
        state["repository_context"] = serialized

        related_file_contents = _read_related_files(selected, target_file)
        state["related_file_contents"] = related_file_contents

        emit_success(
            run_context,
            "context_builder_node",
            task,
            {"num_selected": len(selected), "total_symbols": context_pkg.total_symbols, "used_graph": used_graph, "related_files_read": len(related_file_contents)},
            start,
        )
        return {"repository_context": serialized, "related_file_contents": related_file_contents}
    except Exception as e:
        emit_failure(run_context, "context_builder_node", task, str(e), start)
        raise


_MAX_RELATED_FILES = 5
_MAX_CHARS_PER_FILE = 3000


def _read_related_files(selected: list[str], target_file: str | None) -> dict[str, str]:
    """Read the contents of selected related files, excluding the target file.

    Caps at _MAX_RELATED_FILES files and _MAX_CHARS_PER_FILE chars per file.
    Files that cannot be read are silently skipped.
    """
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


def _select_files_from_graph(
    task: str,
    graph_json: Path,
    repo_path: str,
    target_file: str | None,
    max_files: int,
) -> list[str]:
    """Select files from the graphify graph most relevant to the task.

    Scores graph nodes by keyword overlap with the task description, expands
    the selection via one BFS hop, then resolves relative source_file paths to
    absolute paths so they match the RepositorySnapshot produced by
    SimpleRepositoryIndexer.
    """
    data = json.loads(graph_json.read_text(encoding="utf-8"))
    nodes: dict[str, dict] = {n["id"]: n for n in data.get("nodes", [])}

    adj: dict[str, set[str]] = {nid: set() for nid in nodes}
    for link in data.get("links", []):
        src, tgt = link.get("source"), link.get("target")
        if src in adj and tgt in adj:
            adj[src].add(tgt)
            adj[tgt].add(src)

    task_words = {
        w for w in re.findall(r"[a-z0-9_]+", task.lower())
        if len(w) >= 3 and w not in _STOPWORDS
    }

    seed_scores: dict[str, float] = {}
    for nid, ndata in nodes.items():
        label_words = set(re.findall(r"[a-z0-9_]+", ndata.get("label", "").lower()))
        overlap = len(task_words & label_words)
        if overlap:
            seed_scores[nid] = overlap / max(len(task_words), 1)

    top_seeds = sorted(seed_scores, key=lambda n: -seed_scores[n])[:20]
    relevant: set[str] = set(top_seeds)
    for seed in top_seeds[:10]:
        relevant.update(adj.get(seed, set()))

    file_scores: dict[str, float] = {}
    repo = Path(repo_path)
    for nid in relevant:
        source_file = nodes[nid].get("source_file")
        if not source_file:
            continue
        abs_path = str((repo / source_file).resolve())
        file_scores[abs_path] = max(file_scores.get(abs_path, 0.0), seed_scores.get(nid, 0.1))

    result: list[str] = []
    if target_file:
        file_scores.pop(target_file, None)
        result.append(target_file)

    result.extend(sorted(file_scores, key=lambda f: -file_scores[f]))
    return result[:max_files]
