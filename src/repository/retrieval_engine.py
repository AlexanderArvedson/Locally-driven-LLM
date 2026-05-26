"""Deterministic retrieval engine and a simple implementation.

The retrieval engine consumes a `RepositorySnapshot` and returns an
ordered list of file paths according to deterministic heuristics. It does
not perform any prompt formatting or file IO.
"""

from __future__ import annotations

from typing import Protocol, Sequence, Optional, List
import os
import re

from src.repository.repository_types import RepositorySnapshot


class RetrievalEngine(Protocol):
    """Interface for deterministic file selection."""

    def select_files(self, task: str, snapshot: RepositorySnapshot, target_file: Optional[str] = None, max_files: int = 15) -> Sequence[str]:
        """Return a deterministic, ordered list of file paths.

        Args:
            task: task description (opaque to retrieval heuristics)
            snapshot: RepositorySnapshot to query
            target_file: optional path to prioritize
            max_files: hard cap for returned files
        """
        ...


class SimpleRetrievalEngine:
    """A deterministic, heuristic-based retrieval engine.

     Ordering rules (deterministic, score-based):
     1. target file (if provided)
     2. rank remaining files by weighted features:
         - imported directly by target (highest)
         - reverse dependencies of target
         - nearby tests (same directory, then global tests)
         - neighboring files in same directory
         - task keyword matches in filename/symbol names
     3. deterministic tie-break by normalized file path

    Matching of module -> file is heuristic-only: we match by filename
    basename against the import's last component (no module resolution).
    """

    def select_files(self, task: str, snapshot: RepositorySnapshot, target_file: Optional[str] = None, max_files: int = 15) -> List[str]:
        results: List[str] = []

        path_to_node = {f.path: f for f in snapshot.files}
        files_sorted = sorted(snapshot.files, key=lambda x: x.path)

        # Always keep target first when provided and present in the snapshot.
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

            # Higher tuple values rank first; path is deterministic tie-breaker.
            score = (
                direct_imported_by_target,
                imports_target,
                same_dir_test,
                int(is_test),
                same_dir,
                term_hits,
            )
            ranked.append((score, path))

        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
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
