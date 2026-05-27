"""Repository-state helpers for deterministic workflow execution."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class RepositoryStateSnapshot:
    """Minimal snapshot of the repository state used by execution guards."""

    repository_path: Path
    repository_revision: str
    is_clean: bool


def _run_git(repository_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=repository_path,
        check=True,
        capture_output=True,
        text=True,
    )


def get_repository_revision(repository_path: Path) -> str:
    """Return the current git commit SHA for the repository."""

    result = _run_git(repository_path, "rev-parse", "HEAD")
    return result.stdout.strip()


def is_repository_clean(repository_path: Path) -> bool:
    """Return True when git reports no working tree changes."""

    result = _run_git(repository_path, "status", "--porcelain")
    return result.stdout.strip() == ""


def capture_repository_state(repository_path: Path) -> RepositoryStateSnapshot:
    """Capture the current repository revision and cleanliness flag."""

    return RepositoryStateSnapshot(
        repository_path=repository_path,
        repository_revision=get_repository_revision(repository_path),
        is_clean=is_repository_clean(repository_path),
    )


def assert_clean_repository(repository_path: Path) -> RepositoryStateSnapshot:
    """Raise when the repository is dirty, otherwise return its snapshot."""

    snapshot = capture_repository_state(repository_path)
    if not snapshot.is_clean:
        raise RuntimeError(f"Repository is dirty: {repository_path}")
    return snapshot


def restore_repository_state(repository_path: Path) -> None:
    """Reset tracked and untracked changes to the current HEAD state.

    This is intended for failed mutation cleanup in the executor boundary.
    """

    _run_git(repository_path, "reset", "--hard", "HEAD")
    _run_git(repository_path, "clean", "-fd")
