"""Context assembler — builds bounded ContextPackage from ranked files.

ContextAssembler consumes a RepositorySnapshot and a ranked list of selected
file paths, returning a deterministic ContextPackage. It performs no file IO
and does not interact with the graph or LLM layers.
"""

from __future__ import annotations

from typing import Protocol, Sequence, List, Optional

from src.retrieval.contracts.types import ContextPackage, RepositorySnapshot


class ContextAssemblerProtocol(Protocol):
    """Interface for bounded context assembly."""

    def build(
        self,
        task: str,
        target_file: Optional[str],
        selected_files: Sequence[str],
        snapshot: RepositorySnapshot,
        *,
        max_files: int = 15,
        max_symbols_per_file: int = 20,
        max_total_context_chars: int = 30_000,
    ) -> ContextPackage:
        """Build and return a bounded ContextPackage.

        Must be deterministic and must not read files from disk.
        """
        ...


class ContextAssembler:
    """Deterministic, capped context assembler that consumes a snapshot.

    Returns a ContextPackage containing related file paths and symbol names
    (capped) derived from the provided RepositorySnapshot.
    """

    def build(
        self,
        task: str,
        target_file: Optional[str],
        selected_files: Sequence[str],
        snapshot: RepositorySnapshot,
        *,
        max_files: int = 15,
        max_symbols_per_file: int = 20,
        max_total_context_chars: int = 30_000,
    ) -> ContextPackage:
        sel = list(selected_files)[:max_files]

        if target_file and target_file in sel:
            sel = [target_file] + [p for p in sel if p != target_file]

        related_symbols = {}
        total_chars = 0
        total_symbols = 0
        deps: List = []

        path_to_node = {f.path: f for f in snapshot.files}

        for path in sel:
            node = path_to_node.get(path)
            if not node:
                related_symbols[path] = []
                continue

            names = [s.name for s in node.symbols][:max_symbols_per_file]
            related_symbols[path] = names
            total_symbols += len(names)

            for e in snapshot.edges:
                if e.from_path == path:
                    deps.append(e)

            for n in names:
                total_chars += len(n)

            if total_chars >= max_total_context_chars:
                break

        deps = sorted(deps, key=lambda e: (e.from_path, e.to_path))

        return ContextPackage(
            primary_file=target_file,
            related_files=sel,
            related_symbols=related_symbols,
            dependency_summary=deps,
            total_symbols=total_symbols,
        )
