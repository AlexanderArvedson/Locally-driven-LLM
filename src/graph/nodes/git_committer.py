"""Git committer node.

Stages the modified target file and creates a git commit on the current
branch. Runs after file_writer so changes are committed before any push.
"""

from __future__ import annotations

import logging
import time

import git

from src.git.branch_manager import commit_file
from src.graph.nodes.support import require_state_value
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success

logger = logging.getLogger(__name__)


async def git_committer_node(state: GraphState, run_context: RunContext) -> dict:
    """Stage and commit the modified target file.

    Expected state keys:
    - ``repo_path``: root of the git repository
    - ``target_file``: absolute path to the file that was written
    - ``task``: used as the commit message body
    - ``branch_name``: the task branch that must be active when committing

    Returns ``commit_sha`` — the hex SHA of the new commit, or ``""`` when
    the file was unchanged and nothing was committed.
    """
    start = time.time()
    task = state.get("task", "")
    try:
        repo_path = require_state_value(state, "repo_path")
        target_file = require_state_value(state, "target_file")
        expected_branch = require_state_value(state, "branch_name")

        # Guard against the user switching branches mid-run, which would cause
        # the commit to land on the wrong branch and the task branch to have
        # no new commits when the PR is created.
        repo = git.Repo(repo_path)
        active_branch = repo.active_branch.name
        if active_branch != expected_branch:
            raise RuntimeError(
                f"Refusing to commit: repo is on '{active_branch}' but the task "
                f"branch is '{expected_branch}'. Check out the task branch before committing."
            )

        message = f"AI: {task}"
        sha = commit_file(repo_path, target_file, message)

        emit_success(
            run_context,
            "git_committer_node",
            {"sha": sha, "committed": bool(sha)},
            start,
        )
        return {"commit_sha": sha}
    except Exception as exc:
        emit_failure(run_context, "git_committer_node", str(exc), start)
        raise
