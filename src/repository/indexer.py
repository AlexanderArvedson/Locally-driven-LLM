"""Repository indexer interfaces.

Skeleton only: no indexing logic yet.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from src.repository.repository_types import RepositorySnapshot


class RepositoryIndexer(Protocol):
    """Interface for repository indexing.

    The indexer builds an immutable `RepositorySnapshot` for a given root
    path. Consumers should operate on the snapshot and not call the
    indexer to perform ad-hoc parsing or file IO.
    """

    def build_snapshot(self, root_path: str) -> RepositorySnapshot:
        """Build and return an immutable repository snapshot for `root_path`."""
        ...

    def get_file_symbols(self, snapshot: RepositorySnapshot, file_path: str) -> Sequence[str]:
        """Return symbol names for a given file from the snapshot."""
        ...

    def get_dependencies(self, snapshot: RepositorySnapshot, file_path: str) -> Sequence[str]:
        """Return dependency target paths for a given file from the snapshot."""
        ...
