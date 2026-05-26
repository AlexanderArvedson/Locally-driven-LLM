"""Context builder interfaces.

Skeleton only: no context assembly yet.
"""

from __future__ import annotations

from typing import Protocol, Sequence


class ContextBuilder(Protocol):
    """Interface for bounded context assembly."""

    def build_context(self, task: str, target_file: str, selected_files: Sequence[str]) -> object:
        """Build and return a bounded context package."""
        ...
