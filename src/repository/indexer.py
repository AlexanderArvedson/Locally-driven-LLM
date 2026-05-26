"""Repository indexer interfaces.

Skeleton only: no indexing logic yet.
"""

from __future__ import annotations

from typing import Protocol, Sequence


class RepositoryIndexer(Protocol):
    """Interface for repository indexing."""

    def build_snapshot(self) -> object:
        """Build and return an immutable repository snapshot."""
        ...

    def get_file_symbols(self, file_path: str) -> Sequence[object]:
        """Return symbols for a given file from the snapshot."""
        ...

    def get_dependencies(self, file_path: str) -> Sequence[object]:
        """Return dependency edges for a given file from the snapshot."""
        ...
