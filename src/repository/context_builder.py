"""Context builder interface and a simple deterministic implementation.

The ContextBuilder consumes a `RepositorySnapshot` and a deterministic list
of `selected_files` produced by the retrieval layer and returns a bounded
ContextPackage. It must not inspect the filesystem or mutate repository
state.
"""

from __future__ import annotations

from typing import Protocol, Sequence, List, Optional

from src.repository.repository_types import ContextPackage, RepositorySnapshot


class ContextBuilder(Protocol):
    """Interface for bounded context assembly."""

    def build_context(self, task: str, target_file: Optional[str], selected_files: Sequence[str], snapshot: RepositorySnapshot, *, max_files: int = 15, max_symbols_per_file: int = 20, max_total_context_chars: int = 30000) -> ContextPackage:
        """Build and return a bounded ContextPackage.

        The implementation must be deterministic and must not read files from
        disk.
        """
        ...


class SimpleContextBuilder:
    """Deterministic, capped context builder that consumes a snapshot.

    It returns a `ContextPackage` containing related file paths and symbol
    names (capped) derived from the provided `RepositorySnapshot`.
    """

    def build_context(self, task: str, target_file: Optional[str], selected_files: Sequence[str], snapshot: RepositorySnapshot, *, max_files: int = 15, max_symbols_per_file: int = 20, max_total_context_chars: int = 30000) -> ContextPackage:
        # enforce deterministic ordering and hard caps
        sel = list(selected_files)[:max_files]

        # ensure target_file is first if present
        if target_file and target_file in sel:
            sel = [target_file] + [p for p in sel if p != target_file]

        related_symbols = {}
        total_chars = 0
        total_symbols = 0
        deps: List = []

        # helper map for quick lookup
        path_to_node = {f.path: f for f in snapshot.files}

        for path in sel:
            node = path_to_node.get(path)
            if not node:
                related_symbols[path] = []
                continue

            # extract symbol names deterministically, cap per-file
            names = [s.name for s in node.symbols][:max_symbols_per_file]
            related_symbols[path] = names
            total_symbols += len(names)

            # dependency summary: include outgoing edges for this file
            for e in snapshot.edges:
                if e.from_path == path:
                    deps.append(e)

            # estimate context char counts conservatively using symbol name lengths
            for n in names:
                total_chars += len(n)

            if total_chars >= max_total_context_chars:
                break

        # deterministic ordering for deps
        deps = sorted(deps, key=lambda e: (e.from_path, e.to_path))

        return ContextPackage(primary_file=target_file, related_files=sel, related_symbols=related_symbols, dependency_summary=deps, total_symbols=total_symbols)
