"""Git branch management for target repositories using GitPython."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

import git
from git.exc import GitCommandError, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Outcome of a repository synchronisation attempt."""

    operation: str          # "clone" | "pull" | "skipped"
    success: bool
    branch: str
    commit_hash: str | None  # 7-char HEAD hex after sync, or None on failure
    already_up_to_date: bool = False
    error: str | None = None


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


def clone_if_missing(
    remote_url: str,
    local_path: str,
    username: str = "",
    token: str = "",
) -> git.Repo:
    """Return the repo at *local_path*, cloning from *remote_url* if absent.

    If *local_path* already contains a valid git repository the clone step is
    skipped and the existing repo is returned. Credentials are embedded in the
    URL so no credential helper is required.
    """
    from pathlib import Path

    path = Path(local_path)

    if path.exists():
        try:
            repo = git.Repo(local_path)
            logger.info("Repository already exists at '%s' — skipping clone.", local_path)
            return repo
        except InvalidGitRepositoryError:
            raise ValueError(
                f"Path '{local_path}' exists but is not a git repository."
            )

    url = _auth_url(remote_url, username, token) if token else remote_url
    logger.info("Cloning '%s' into '%s'…", remote_url, local_path)
    repo = git.Repo.clone_from(url, local_path)
    logger.info("Clone complete.")
    return repo


def ensure_repo_synced(
    remote_url: str,
    local_path: str,
    base_branch: str,
    username: str = "",
    token: str = "",
) -> SyncResult:
    """Clone the repo if absent; otherwise switch to base_branch and pull.

    If the working tree has uncommitted changes the checkout/pull is skipped
    with a warning — this guards against discarding in-progress work that
    should not normally be present in a pipeline-target repo.

    Returns a SyncResult describing what was done.
    """
    from pathlib import Path

    if not Path(local_path).exists():
        repo = clone_if_missing(remote_url, local_path, username, token)
        commit_hash = repo.head.commit.hexsha[:7]
        return SyncResult(operation="clone", success=True, branch=base_branch, commit_hash=commit_hash)

    repo = _open_repo(local_path)
    if repo.is_dirty(untracked_files=False):
        logger.warning(
            "Working tree at '%s' has uncommitted changes — skipping checkout/pull.",
            local_path,
        )
        return SyncResult(operation="skipped", success=True, branch=base_branch, commit_hash=None)

    try:
        repo.git.checkout(base_branch)
    except GitCommandError as exc:
        logger.warning("Could not checkout '%s': %s", base_branch, exc.stderr.strip())

    head_before = repo.head.commit.hexsha[:7]
    try:
        repo.remotes.origin.pull(base_branch)
        head_after = repo.head.commit.hexsha[:7]
        already_up_to_date = head_before == head_after
        logger.info("Pulled '%s' at '%s'.", base_branch, local_path)
        return SyncResult(
            operation="pull",
            success=True,
            branch=base_branch,
            commit_hash=head_after,
            already_up_to_date=already_up_to_date,
        )
    except GitCommandError as exc:
        logger.warning("Could not pull '%s': %s", base_branch, exc.stderr.strip())
        return SyncResult(
            operation="pull",
            success=False,
            branch=base_branch,
            commit_hash=head_before,
            error=exc.stderr.strip() if exc.stderr else str(exc),
        )


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
    Raises RuntimeError if the working tree has uncommitted changes that
    would prevent the checkout — this typically means a previous run was
    interrupted after writing the file but before committing it.
    """
    repo = _open_repo(repo_path)
    branch_name = build_branch_name(prefix, task)

    if repo.is_dirty(untracked_files=False):
        dirty_files = (
            [item.a_path for item in repo.index.diff(None)]
            + [item.a_path for item in repo.index.diff("HEAD")]
        )
        raise RuntimeError(
            f"Working tree has uncommitted changes, cannot checkout branch.\n"
            f"Affected files: {dirty_files}\n"
            "This usually means a previous run was interrupted after writing "
            "the file but before committing. Run `git checkout -- .` in the "
            "repository to discard the changes and retry."
        )

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
    nothing to commit (file unchanged on disk). Handles both tracked
    (modified) and untracked (new) files.
    """
    repo = _open_repo(repo_path)
    rel_path = os.path.relpath(file_path, repo_path)
    # Git uses forward slashes internally; normalise for the untracked check.
    rel_path_fwd = rel_path.replace("\\", "/")

    is_new = rel_path_fwd in repo.untracked_files
    if not is_new and not repo.is_dirty(path=rel_path, untracked_files=False):
        logger.info("Nothing to commit for '%s' — file unchanged.", rel_path)
        return ""

    repo.index.add([rel_path])
    commit = repo.index.commit(message)
    logger.info("Committed '%s' as %s.", rel_path, commit.hexsha[:8])
    return commit.hexsha


def get_diff_stat(repo_path: str, base_branch: str) -> str:
    """Return a human-readable diff --stat between origin/<base_branch> and HEAD."""
    repo = _open_repo(repo_path)
    try:
        return repo.git.diff(f"origin/{base_branch}...HEAD", stat=True).strip()
    except GitCommandError as exc:
        logger.warning("Could not compute diff stat: %s", exc)
        return ""


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
