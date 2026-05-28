"""Git branch management for target repositories.

Provides utilities to create task branches in the repositories listed
in config.json. All operations use subprocess + the system `git` binary
so no third-party git library is required.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r"[^\w\-]+")
_MULTI_HYPHEN = re.compile(r"-{2,}")
_MAX_TASK_SLUG_LEN = 50


def _sanitize_task_slug(task: str) -> str:
    """Convert a free-text task description into a safe branch-name segment."""
    slug = task.lower().strip()
    slug = _UNSAFE_CHARS.sub("-", slug)
    slug = _MULTI_HYPHEN.sub("-", slug)
    slug = slug.strip("-")
    return slug[:_MAX_TASK_SLUG_LEN].rstrip("-")


def build_branch_name(prefix: str, task: str) -> str:
    """Return the full branch name: ``<prefix><sanitized-task>``."""
    return f"{prefix}{_sanitize_task_slug(task)}"


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def branch_exists(repo_path: str, branch_name: str) -> bool:
    """Return True if *branch_name* exists locally in the repo."""
    result = subprocess.run(
        ["git", "branch", "--list", branch_name],
        cwd=Path(repo_path),
        capture_output=True,
        text=True,
    )
    return branch_name in result.stdout


def push_branch(
    repo_path: str,
    branch_name: str,
    remote_url: str,
    username: str,
    token: str,
) -> None:
    """Push *branch_name* to the authenticated remote URL.

    Embeds credentials in the remote URL so no credential helper config is
    required on the machine.
    """
    cwd = Path(repo_path)

    # Build an authenticated URL: https://user:token@github.com/owner/repo.git
    if remote_url.startswith("https://"):
        auth_url = remote_url.replace("https://", f"https://{username}:{token}@", 1)
    else:
        auth_url = remote_url

    _run_git(["push", "--set-upstream", auth_url, branch_name], cwd)
    logger.info("Pushed branch '%s' to remote.", branch_name)


def create_task_branch(
    repo_path: str,
    base_branch: str,
    prefix: str,
    task: str,
) -> str:
    """Create (and checkout) a new branch in the target repository.

    The branch is created from *base_branch* with name
    ``<prefix><sanitized-task>``. If the branch already exists it is
    checked out without recreating it.

    Returns the full branch name.
    """
    cwd = Path(repo_path)
    branch_name = build_branch_name(prefix, task)

    # Ensure local base_branch is up to date from remote when possible.
    try:
        _run_git(["fetch", "origin", base_branch], cwd)
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "Could not fetch '%s' from origin (continuing anyway): %s",
            base_branch,
            exc.stderr.strip(),
        )

    if branch_exists(repo_path, branch_name):
        logger.info("Branch '%s' already exists — checking it out.", branch_name)
        _run_git(["checkout", branch_name], cwd)
    else:
        _run_git(["checkout", "-b", branch_name, f"origin/{base_branch}"], cwd)
        logger.info("Created and checked out branch '%s' from '%s'.", branch_name, base_branch)

    return branch_name
