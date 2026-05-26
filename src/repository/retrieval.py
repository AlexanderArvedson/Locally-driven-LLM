"""Deterministic retrieval engine and a simple implementation.

The retrieval engine consumes a `RepositorySnapshot` and returns an
ordered list of file paths according to deterministic heuristics. It does
not perform any prompt formatting or file IO.
"""

from __future__ import annotations

from typing import Protocol, Sequence, Optional, List
import os

from src.repository.types import RepositorySnapshot


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

    Ordering rules (deterministic):
    1. target file (if provided)
    2. files corresponding to imported modules by the target
    3. reverse dependencies (files importing the target)
    4. nearby tests (files under `tests/` or starting with `test_` in same dir)
    5. neighboring files (same directory)

    Matching of module -> file is heuristic-only: we match by filename
    basename against the import's last component (no module resolution).
    """

    def select_files(self, task: str, snapshot: RepositorySnapshot, target_file: Optional[str] = None, max_files: int = 15) -> List[str]:
        results: List[str] = []
        seen = set()

        def add(path: str):
            if path and path not in seen:
                seen.add(path)
                results.append(path)

        # helper maps
        path_to_node = {f.path: f for f in snapshot.files}

        # 1) target file
        if target_file and target_file in path_to_node:
            add(target_file)

        # derive target basename for heuristic matching
        target_basename = None
        target_imports = []
        if target_file and target_file in path_to_node:
            tn = path_to_node[target_file]
            target_basename = tn.path.split(os.path.sep)[-1].rsplit(".py", 1)[0]
            target_imports = tn.imports

        # 2) imported modules by target -> map to files whose basename matches import last component
        if target_imports:
            for imp in target_imports:
                last = imp.split(".")[-1]
                for f in snapshot.files:
                    fname = f.path.split(os.path.sep)[-1]
                    stem = fname.rsplit(".py", 1)[0]
                    if stem == last:
                        add(f.path)

        # 3) reverse dependencies: files that import the target basename
        if target_basename:
            for f in snapshot.files:
                if f.path == target_file:
                    continue
                for imp in f.imports:
                    if imp.split(".")[-1] == target_basename:
                        add(f.path)
                        break

        # 4) nearby tests: deterministic scan of snapshot for test files, prefer same directory first
        if target_file:
            target_dir = os.path.dirname(target_file)
            # tests in same dir
            for f in sorted(snapshot.files, key=lambda x: x.path):
                if os.path.dirname(f.path) == target_dir and (f.path.startswith("tests") or f.path.split(os.path.sep)[-1].startswith("test_")):
                    add(f.path)
            # then global tests
            for f in sorted(snapshot.files, key=lambda x: x.path):
                if (f.path.startswith("tests") or f.path.split(os.path.sep)[-1].startswith("test_")):
                    add(f.path)

        # 5) neighboring files (same directory)
        if target_file:
            target_dir = os.path.dirname(target_file)
            for f in sorted(snapshot.files, key=lambda x: x.path):
                if os.path.dirname(f.path) == target_dir:
                    add(f.path)

        # fallback: top-level files deterministically until max_files
        for f in sorted(snapshot.files, key=lambda x: x.path):
            add(f.path)
            if len(results) >= max_files:
                break

        # enforce hard cap and return
        return results[:max_files]

