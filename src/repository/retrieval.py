"""Retrieval engine interfaces.

Skeleton only: no retrieval logic yet.
"""

from __future__ import annotations

from typing import Protocol, Sequence


class RetrievalEngine(Protocol):
    """Interface for deterministic file selection."""

    def select_files(self, task: str, snapshot: object) -> Sequence[str]:
        """Return a deterministic, ordered list of file paths."""
        ...
