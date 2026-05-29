"""Git branch management for target repositories using GitPython."""

from __future__ import annotations

import logging
import re

import git
from git.exc import GitCommandError, InvalidGitRepositoryError

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r"[^\w\-]+")
_MULTI_HYPHEN = re.compile(r"-{2,}")
_MAX_TASK_SLUG_LEN = 50


def _sanitize_task_slug(task: str) -> str:
    slug = task.lower().strip()
    slug = _UNSAFE_CHARS.sub("-", slug)
    slug = _MULTI_HYPHEN.sub("-", slug)
    slug = slug.strip("-")
    return slug[:_MAX_TASK_SLUG_LEN].rstrip("-")


def build_branch_name(prefix: str, task: str) -> str:
    """Return the full branch name: ``<prefix><sanitized-task>``."""
    return f"{prefix}{_sanitize_task_slug(task)}"


def _open_repo(repo_path: str) -> git.Repo:
    try:
        return git.Repo(repo_path)
    except InvalidGitRepositoryError:
        raise ValueError(f"Not a git repository: {repo_path}")


def _auth_url(remote_url: str, username: str, token: str) -> str:
    if remote_url.startswith("https://"):
        return remote_url.replace("https://", f"https://{username}:{token}@", 1)
    return remote_url


def branch_exists(repo_path: str, branch_name: str) -> bool:
    """Return True if *branch_name* exists locally."""
    repo = _open_repo(repo_path)
    return branch_name in [b.name for b in repo.branches]


def create_task_branch(
    repo_path: str,
    base_branch: str,
    prefix: str,
    task: str,
) -> str:
    """Create (or check out) a task branch from *base_branch*.

    Returns the full branch name.
    """
    repo = _open_repo(repo_path)
    branch_name = build_branch_name(prefix, task)

    try:
        repo.remote("origin").fetch(base_branch)
    except GitCommandError as exc:
        logger.warning(
            "Could not fetch '%s' from origin (continuing anyway): %s",
            base_branch,
            exc.stderr.strip(),
        )

    if branch_name in [b.name for b in repo.branches]:
        logger.info("Branch '%s' already exists — checking it out.", branch_name)
        repo.git.checkout(branch_name)
    else:
        repo.git.checkout("-b", branch_name, f"origin/{base_branch}")
        logger.info("Created and checked out branch '%s' from '%s'.", branch_name, base_branch)

    return branch_name


def commit_file(
    repo_path: str,
    file_path: str,
    message: str,
) -> str:
    """Stage *file_path* and create a commit in the repo.

    Returns the hex SHA of the new commit, or an empty string if there was
    nothing to commit (file unchanged on disk).
    """
    repo = _open_repo(repo_path)

    repo.index.add([file_path])

    if not repo.index.diff("HEAD"):
        logger.info("Nothing to commit for '%s' — file unchanged.", file_path)
        return ""

    commit = repo.index.commit(message)
    logger.info("Committed '%s' as %s.", file_path, commit.hexsha[:8])
    return commit.hexsha


def push_branch(
    repo_path: str,
    branch_name: str,
    remote_url: str,
    username: str,
    token: str,
) -> None:
    """Push *branch_name* to the authenticated remote URL."""
    repo = _open_repo(repo_path)
    url = _auth_url(remote_url, username, token)

    try:
        repo.git.push(url, branch_name)
        logger.info("Pushed branch '%s' to remote.", branch_name)
    except GitCommandError as exc:
        raise RuntimeError(
            f"git push failed (exit {exc.status}):\n{exc.stderr.strip()}"
        ) from None
