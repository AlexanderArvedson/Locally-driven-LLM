"""Branch creator node.

Creates (or checks out) a task branch in the target repository before
any file reads or code generation takes place. This is the first node
executed in the workflow.
"""

from __future__ import annotations

import logging
import time

from src.core.config_loader import get_repository_config
from src.git.branch_manager import clone_if_missing, create_task_branch
from src.graph.nodes.support import require_state_value
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success

logger = logging.getLogger(__name__)


async def branch_creator_node(state: GraphState, run_context: RunContext) -> dict:
    """Create a task branch in the target repository.

    Reads ``repo_path`` and ``task`` from state, derives the branch name
    from the repository's configured prefix and base_branch, and checks
    out (or creates) that branch.

    Returns a dict with:
    - ``branch_name``: the full branch name that was created/checked out.
    """
    start = time.time()
    try:
        repo_path = require_state_value(state, "repo_path")
        task = require_state_value(state, "task")

        repo_config = get_repository_config(repo_path)
        credentials = repo_config.credentials or {}

        clone_if_missing(
            remote_url=repo_config.url,
            local_path=repo_path,
            token=credentials.get("token", ""),
        )

        branch_name = create_task_branch(
            repo_path=repo_path,
            base_branch=repo_config.base_branch,
            prefix=repo_config.prefix,
            task=task,
        )

        emit_success(
            run_context,
            "branch_creator_node",
            {"branch_name": branch_name},
            start,
        )
        return {"branch_name": branch_name}
    except Exception as exc:
        emit_failure(run_context, "branch_creator_node", str(exc), start)
        raise
