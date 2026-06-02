"""Heuristic file ranker — deterministic, graph-free retrieval.

HeuristicRanker scores repository files using import relationships, directory
proximity, and task keyword matches. It is the fallback when no knowledge
graph is available.
"""

from __future__ import annotations

import os
import re
from typing import Protocol, Sequence, Optional, List

from src.retrieval.contracts.types import RepositorySnapshot


class RankerProtocol(Protocol):
    """Interface for file ranking strategies."""

    def rank_candidates(
        self,
        task: str,
        snapshot: RepositorySnapshot,
        target_file: Optional[str] = None,
        max_files: int = 15,
    ) -> List[str]:
        """Return a deterministic, ordered list of file paths."""
        ...


class HeuristicRanker:
    """Deterministic, heuristic-based file ranker.

    Ordering rules (score-based, deterministic tie-break by path):
    1. Target file always first (when provided and in snapshot).
    2. Remaining files ranked by feature tuple:
        - directly imported by target file (highest weight)
        - imports target file
        - test in same directory as target
        - any test file
        - same directory as target
        - task keyword hits in filename/symbol names
    """

    def rank_candidates(
        self,
        task: str,
        snapshot: RepositorySnapshot,
        target_file: Optional[str] = None,
        max_files: int = 15,
    ) -> List[str]:
        results: List[str] = []

        path_to_node = {f.path: f for f in snapshot.files}
        files_sorted = sorted(snapshot.files, key=lambda x: x.path)

        if target_file and target_file in path_to_node:
            results.append(target_file)

        target_node = path_to_node.get(target_file) if target_file else None
        target_dir = os.path.dirname(target_file) if target_file else None
        target_basename = target_file.split(os.path.sep)[-1].rsplit(".py", 1)[0] if target_file else ""
        target_import_last = {
            imp.split(".")[-1]
            for imp in (target_node.imports if target_node else [])
        }

        task_terms = self._task_terms(task)

        ranked: list[tuple[tuple[int, int, int, int, int, int], str]] = []
        for node in files_sorted:
            path = node.path
            if path == target_file:
                continue

            filename = path.split(os.path.sep)[-1]
            stem = filename.rsplit(".py", 1)[0]
            is_test = self._is_test_path(path)
            same_dir = int(target_dir is not None and os.path.dirname(path) == target_dir)
            same_dir_test = int(is_test and same_dir == 1)
            imports_target = int(
                bool(target_basename) and any(imp.split(".")[-1] == target_basename for imp in node.imports)
            )
            direct_imported_by_target = int(stem in target_import_last)
            term_hits = self._task_term_hits(task_terms, stem, [sym.name for sym in node.symbols])

            score = (
                direct_imported_by_target,
                imports_target,
                same_dir_test,
                int(is_test),
                same_dir,
                term_hits,
            )
            ranked.append((score, path))

        # Sort by score descending, then by path ascending for a deterministic
        # tie-break. Negating each score component avoids reverse=True on the
        # whole tuple, which would incorrectly sort equal-score paths descending.
        ranked.sort(key=lambda item: (tuple(-x for x in item[0]), item[1]))
        results.extend([path for _score, path in ranked])
        return results[:max_files]

    @staticmethod
    def _is_test_path(path: str) -> bool:
        norm = os.path.normpath(path)
        base = os.path.basename(norm)
        return norm.startswith("tests" + os.path.sep) or base.startswith("test_")

    @staticmethod
    def _task_terms(task: str) -> set[str]:
        parts = re.findall(r"[A-Za-z0-9_]+", task.lower())
        return {p for p in parts if len(p) >= 3}

    @staticmethod
    def _task_term_hits(task_terms: set[str], stem: str, symbols: list[str]) -> int:
        if not task_terms:
            return 0
        haystack = [stem.lower()] + [s.lower() for s in symbols]
        hits = 0
        for term in task_terms:
            if any(term in item for item in haystack):
                hits += 1
        return hits
