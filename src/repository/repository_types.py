"""Repository snapshot types for Phase 2.

These are minimal, structural-only dataclasses/TypedDicts used to stabilize
contracts between indexer, retrieval, and context builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Symbol:
    """Represents a top-level symbol extracted from a file."""

    name: str
    kind: str  # e.g. 'function', 'class', 'method'
    lineno: Optional[int] = None
    docstring: Optional[str] = None


@dataclass(frozen=True)
class DependencyEdge:
    """Represents a directed import relationship between files."""

    from_path: str
    to_path: str
    import_text: Optional[str] = None


@dataclass(frozen=True)
class FileNode:
    """Metadata for a single file in the repository snapshot."""

    path: str
    language: str
    size: int
    symbols: List[Symbol]
    imports: List[str]


@dataclass(frozen=True)
class RepositorySnapshot:
    """Immutable snapshot of the repository used for deterministic retrieval."""

    files: List[FileNode]
    edges: List[DependencyEdge]

    def get_file(self, path: str) -> Optional[FileNode]:
        for f in self.files:
            if f.path == path:
                return f
        return None


@dataclass(frozen=True)
class ContextPackage:
    """Bounded context package returned by the ContextBuilder.

    Contains only lightweight, deterministic information derived from the
    snapshot: related file paths, a per-file list of symbol names (capped),
    and a small dependency summary. It does not include full file contents.
    """

    primary_file: Optional[str]
    related_files: List[str]
    related_symbols: dict
    dependency_summary: List[DependencyEdge]
    total_symbols: int
