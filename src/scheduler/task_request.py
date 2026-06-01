from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TaskRequest:
    """External request contract for submitting a task to the workflow.

    Separates the user-facing API from internal GraphState, ensuring there
    is exactly one validated entry point into the workflow.
    """

    # Natural-language description of the mutation to perform.
    task: str

    # Absolute path to the repository root.
    repo_path: str

    # Repo-relative path to the primary target file, or None to let
    # the retrieval pipeline select files autonomously.
    target_path: str | None = None

    # Allow the retrieval pipeline to include supporting files in context.
    allow_multi_file: bool = True

    # Maximum number of files the retrieval pipeline may surface.
    max_files: int = 10
