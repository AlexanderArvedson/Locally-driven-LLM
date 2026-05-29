"""Repository indexer protocol.

Defines the RepositoryIndexer interface that all indexer implementations must
satisfy. Consumers should operate on the resulting RepositorySnapshot rather
than calling the indexer for ad-hoc file IO.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from src.retrieval.contracts.types import RepositorySnapshot


class RepositoryIndexer(Protocol):
    """Interface for repository indexing."""

    def build_snapshot(self, root_path: str) -> RepositorySnapshot:
        """Build and return an immutable repository snapshot for `root_path`."""
        ...

    def get_file_symbols(self, snapshot: RepositorySnapshot, file_path: str) -> Sequence[str]:
        """Return symbol names for a given file from the snapshot."""
        ...

    def get_dependencies(self, snapshot: RepositorySnapshot, file_path: str) -> Sequence[str]:
        """Return dependency target paths for a given file from the snapshot."""
        ...
