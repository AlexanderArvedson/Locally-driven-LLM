"""Graph query utilities for the retrieval pipeline.

GraphQuery loads graph.json once and exposes keyword-based candidate retrieval
and dependency-aware BFS expansion. It acts as the index substrate for the
retrieval pipeline — graph content never surfaces as prompt context.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from collections import deque


_STOPWORDS = {
    "the", "a", "an", "in", "of", "to", "for", "and", "or", "is", "it",
    "be", "this", "that", "with", "from", "by", "we", "i", "add", "use",
}


class GraphQuery:
    """Loads graph.json once and exposes keyword + dependency queries.

    Constructed via `GraphQuery.from_path`; never instantiated directly so
    callers cannot bypass SHA validation.

    Attributes:
        graph_snapshot_sha: The repo HEAD SHA recorded in graph_meta.json at
            load time. Retrieval results are tied to this SHA.
    """

    def __init__(self, nodes: dict[str, dict], adj: dict[str, set[str]], graph_snapshot_sha: str) -> None:
        self._nodes = nodes
        self._adj = adj
        self.graph_snapshot_sha = graph_snapshot_sha

    @classmethod
    def from_path(cls, graph_dir: Path, expected_sha: str) -> "GraphQuery":
        """Load graph.json from `graph_dir` and return a GraphQuery instance.

        Reads graph_meta.json to populate `graph_snapshot_sha`; uses
        `expected_sha` as the authoritative SHA rather than re-reading HEAD
        so the retrieval node stays deterministic within a single run.

        Raises FileNotFoundError if graph.json is missing.
        """
        graph_json = graph_dir / "graph.json"
        if not graph_json.exists():
            raise FileNotFoundError(f"graph.json not found at {graph_dir}")

        data = json.loads(graph_json.read_text(encoding="utf-8"))
        nodes: dict[str, dict] = {n["id"]: n for n in data.get("nodes", [])}

        adj: dict[str, set[str]] = {nid: set() for nid in nodes}
        for link in data.get("links", []):
            src, tgt = link.get("source"), link.get("target")
            if src in adj and tgt in adj:
                adj[src].add(tgt)
                adj[tgt].add(src)

        # Prefer SHA from meta file; fall back to expected_sha if meta is absent.
        meta_path = graph_dir / "graph_meta.json"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sha = meta.get("repo_sha", expected_sha)
        except (OSError, json.JSONDecodeError):
            sha = expected_sha

        return cls(nodes=nodes, adj=adj, graph_snapshot_sha=sha)

    def query_by_keywords(self, task_words: set[str], top_k: int = 20) -> list[tuple[str, float]]:
        """Return (node_id, score) pairs ranked by keyword overlap with task words.

        Score is overlap_count / max(len(task_words), 1) — a normalised value
        in [0, 1]. Only nodes with at least one overlapping keyword are returned.
        """
        scored: list[tuple[str, float]] = []
        for nid, ndata in self._nodes.items():
            label_words = set(re.findall(r"[a-z0-9_]+", ndata.get("label", "").lower()))
            overlap = len(task_words & label_words)
            if overlap:
                scored.append((nid, overlap / max(len(task_words), 1)))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    def expand_by_dependency(self, node_ids: list[str], hops: int = 1) -> list[str]:
        """BFS expansion: return all node_ids reachable within `hops` edges.

        Includes the original `node_ids` in the result. Deduplicates while
        preserving BFS discovery order (breadth-first, then input order).
        """
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()

        for nid in node_ids:
            if nid in self._adj:
                queue.append((nid, 0))
                visited.add(nid)

        result: list[str] = []
        while queue:
            current, depth = queue.popleft()
            result.append(current)
            if depth < hops:
                for neighbor in self._adj.get(current, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))

        return result

    def files_for_nodes(self, node_ids: list[str], repo_path: str) -> dict[str, float]:
        """Map resolved absolute file paths to their highest node score.

        Nodes without a `source_file` attribute are silently skipped.
        Paths are resolved relative to `repo_path`.
        """
        repo = Path(repo_path)
        file_scores: dict[str, float] = {}
        for nid in node_ids:
            ndata = self._nodes.get(nid, {})
            source_file = ndata.get("source_file")
            if not source_file:
                continue
            abs_path = str((repo / source_file).resolve())
            # Keep the highest score when multiple nodes map to the same file.
            file_scores[abs_path] = max(file_scores.get(abs_path, 0.0), 0.1)
        return file_scores

    def files_for_scored_nodes(
        self,
        scored_nodes: list[tuple[str, float]],
        repo_path: str,
    ) -> dict[str, float]:
        """Like `files_for_nodes` but preserves per-node scores.

        Maps each absolute file path to the maximum score of any node that
        belongs to that file, using the scores from `scored_nodes`.
        """
        repo = Path(repo_path)
        file_scores: dict[str, float] = {}
        for nid, score in scored_nodes:
            ndata = self._nodes.get(nid, {})
            source_file = ndata.get("source_file")
            if not source_file:
                continue
            abs_path = str((repo / source_file).resolve())
            file_scores[abs_path] = max(file_scores.get(abs_path, 0.0), score)
        return file_scores

    @staticmethod
    def task_words(task: str) -> set[str]:
        """Extract normalised, non-stopword tokens from a task string."""
        return {
            w for w in re.findall(r"[a-z0-9_]+", task.lower())
            if len(w) >= 3 and w not in _STOPWORDS
        }
