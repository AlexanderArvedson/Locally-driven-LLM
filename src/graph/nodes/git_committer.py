"""Git committer node.

Stages the modified target file and creates a git commit on the current
branch. Runs after file_writer so changes are committed before any push.
"""

from __future__ import annotations

import logging
import time

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

    Returns an empty dict — this node exists for its git side-effect only.
    """
    start = time.time()
    task = state.get("task", "")
    try:
        repo_path = require_state_value(state, "repo_path")
        target_file = require_state_value(state, "target_file")

        message = f"AI: {task}"
        sha = commit_file(repo_path, target_file, message)

        emit_success(
            run_context,
            "git_committer_node",
            task,
            {"sha": sha, "committed": bool(sha)},
            start,
        )
        return {}
    except Exception as exc:
        emit_failure(run_context, "git_committer_node", task, str(exc), start)
        raise
