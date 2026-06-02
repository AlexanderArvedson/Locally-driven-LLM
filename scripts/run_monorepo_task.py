"""Run a single task against the configured monorepo, then push the branch and open a PR.

Usage (from the project root):

    python scripts/run_monorepo_task.py
    python scripts/run_monorepo_task.py --task "Add docstrings to all public functions"
    python scripts/run_monorepo_task.py --task "Add type hints" --target-file app/models/task.py

The script reads repository settings (local_path, url, credentials, prefix,
base_branch) from config.json, so no extra flags are needed for auth or paths.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import APP_CONFIG  # noqa: E402
from src.git.branch_manager import build_branch_name, get_diff_stat, push_branch  # noqa: E402
from src.git.pr_creator import create_pull_request  # noqa: E402
from src.graph.workflow import make_graph  # noqa: E402
from src.observability.context import RunContext  # noqa: E402
from src.observability.logger import format_run_console, write_run_summary  # noqa: E402
from src.scheduler.state_factory import GraphStateFactory  # noqa: E402
from src.scheduler.task_request import TaskRequest  # noqa: E402


DEFAULT_TASK = "Add a docstring to each public function that is currently missing one."


def _pick_repo():
    """Return the first repository config entry."""
    if not APP_CONFIG.repositories:
        raise RuntimeError("No repositories configured in config.json")
    return APP_CONFIG.repositories[0]


async def _run_workflow(repo_path: str, task: str, target_file: str | None) -> tuple[dict, RunContext]:
    run_context = RunContext.new()
    graph = make_graph(run_context)
    request = TaskRequest(
        task=task,
        repo_path=repo_path,
        target_path=target_file,
    )
    result = await graph.ainvoke(GraphStateFactory.from_task_request(request))
    return result, run_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a task against the configured monorepo and open a PR.")
    parser.add_argument("--task", default=DEFAULT_TASK, help="Prompt describing what the LLM should do.")
    parser.add_argument("--target-file", default=None, help="Relative path inside the repo to target (optional).")
    args = parser.parse_args()

    repo = _pick_repo()
    repo_path = repo.local_path
    task = args.task

    target_file: str | None = None
    if args.target_file:
        target_file = str(Path(repo_path) / args.target_file)

    print(f"Repository : {repo.name} ({repo_path})")
    print(f"Base branch: {repo.base_branch}")
    print(f"Prefix     : {repo.prefix}")
    print(f"Task       : {task}")
    if target_file:
        print(f"Target file: {target_file}")
    print()

    expected_branch = build_branch_name(repo.prefix, task)
    print(f"Expected branch: {expected_branch}")
    print()

    # ── 1. Run workflow (creates branch, modifies file) ──────────────────────
    print("Running workflow…")
    result, run_context = asyncio.run(_run_workflow(repo_path, task, target_file))

    branch_name: str = result.get("branch_name", expected_branch)
    updated_code = result.get("updated_code")
    commit_sha: str = result.get("commit_sha", "")

    final_status = "success" if updated_code and commit_sha else "no_changes"
    write_run_summary(run_context, final_status)
    print(format_run_console(run_context, final_status))
    print()

    print(f"Branch created : {branch_name}")
    print(f"File modified  : {'yes' if updated_code else 'no'}")
    print(f"Commit SHA     : {commit_sha or '(none)'}")
    print()

    if not updated_code:
        print("Workflow finished but no file was written — skipping push and PR.")
        return 0

    if not commit_sha:
        print("File was written but git found no changes to commit (content unchanged) — skipping push and PR.")
        return 0

    # ── 2. Push branch ───────────────────────────────────────────────────────
    credentials = repo.credentials or {}
    username = credentials.get("username", "")
    token = credentials.get("token", "")

    if not token:
        print("No token configured — skipping push and PR.")
        return 0

    diff_stat = get_diff_stat(repo_path, repo.base_branch)
    if diff_stat:
        print(f"Diff stat:\n{diff_stat}\n")

    print(f"Pushing branch '{branch_name}' to origin…")
    try:
        push_branch(
            repo_path=repo_path,
            branch_name=branch_name,
            remote_url=repo.url,
            username=username,
            token=token,
        )
    except RuntimeError as push_err:
        print(f"Push failed: {push_err}")
        return 1
    print("Push complete.")
    print()

    # ── 3. Create pull request ───────────────────────────────────────────────
    pr_title = f"AI: {task[:72]}"
    pr_body = (
        f"**Task:** {task}\n\n"
        f"**Branch:** `{branch_name}`\n\n"
        + (f"**Changes:**\n```\n{diff_stat}\n```\n\n" if diff_stat else "")
        + "Automated change generated by the locally-driven LangGraph workflow."
    )

    print("Creating pull request…")
    try:
        pr_url = create_pull_request(
            remote_url=repo.url,
            token=token,
            head_branch=branch_name,
            base_branch=repo.base_branch,
            title=pr_title,
            body=pr_body,
        )
    except RuntimeError as pr_err:
        if "No commits between" in str(pr_err):
            print(f"PR skipped: remote branch has no commits ahead of '{repo.base_branch}' (branch: {branch_name}).")
            return 0
        raise

    print(f"Pull request opened: {pr_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
