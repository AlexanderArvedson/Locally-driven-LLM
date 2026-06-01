from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RetrievalRequest:
    """Input contract passed from the scheduler layer to the retrieval pipeline."""

    # Natural-language task description forwarded from TaskRequest.
    task: str

    # Repo-relative path to the primary target file, or None for autonomous selection.
    target_path: str | None

    # Maximum number of files to surface.
    max_files: int


@dataclass(slots=True)
class RetrievalResult:
    """Output contract from the retrieval pipeline, stored in GraphState.

    Downstream nodes (coder, reviewer, committer) consume this object instead
    of reading individual state keys, so the retrieval implementation can be
    replaced without touching any of those nodes.
    """

    # Ordered list of repo-relative paths for the primary files to mutate.
    primary_files: list[str] = field(default_factory=list)

    # Additional files included for context only; not directly mutated.
    supporting_files: list[str] = field(default_factory=list)

    # 0.0–1.0 confidence that the selected files fully cover the task scope.
    confidence: float = 0.0
