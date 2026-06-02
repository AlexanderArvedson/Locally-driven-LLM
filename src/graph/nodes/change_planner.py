"""Change planner node — produces an ordered, symbol-centric execution plan.

Given the full set of affected files from dependency_analyzer_node, this node
asks the LLM to produce an ordered JSON list of ChangePlanStep objects.

Files are pre-ordered topologically (definition files before callers) using the
same directed importer index so the LLM receives a sensible ordering hint.
The LLM then annotates each step with the specific symbol and change needed.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict, deque
from pathlib import Path

from src.config_loader import get_coder_model_config
from src.graph.nodes.support import client, require_state_value
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.contracts.context_contract import format_repository_context_for_prompt
from src.retrieval.indexing.ast_indexer import AstIndexer

logger = logging.getLogger(__name__)

_PLAN_SYSTEM_PROMPT = (
    "You are a code planning assistant. "
    "Given a task and a set of files that need modification, produce an ordered execution plan. "
    "Return ONLY a valid JSON array. No explanation, no markdown."
)

_PLAN_USER_TEMPLATE = """\
[TASK]
{task}

[FILES TO MODIFY — ordered by dependency (definitions first, callers last)]
{file_list}

[INSTRUCTION]
For each file, determine:
- operation: always "modify" unless you must create a new file ("create")
- symbol: the primary symbol (function/class/variable) being changed in that file
- change: a precise one-line description of the change to make
- reason: why this file needs to change (e.g. "rename function definition", "update call site", "update import")

Return a JSON array in this exact format:
[
  {{"file": "<absolute path>", "operation": "modify", "symbol": "<symbol name>", "change": "<what to do>", "reason": "<why>"}},
  ...
]

Important:
- Keep the same file order as the list above (definitions before callers).
- Only include files from the list above.
- Use the absolute paths exactly as given.
"""


async def change_planner_node(state: GraphState, run_context: RunContext) -> dict:
    """Create an ordered, symbol-centric execution plan for multi-file changes.

    State inputs consumed:
      task, affected_files, repository_context, repo_path

    State delta returned:
      change_plan   — list[dict] (ChangePlanStep entries), or
      planner_error — when the LLM returns an unusable plan
    """
    start = time.time()
    try:
        task = state.get("task", "")
        affected_files: list[str] = require_state_value(state, "affected_files")
        repo_path = state.get("repo_path")
        repository_context = state.get("repository_context")
        model_cfg = get_coder_model_config(repo_path)

        # Topologically order the files so the LLM receives a good hint.
        ordered_files = _topological_order(affected_files, repo_path)

        file_list = "\n".join(f"- {f}" for f in ordered_files)
        user_prompt = _PLAN_USER_TEMPLATE.format(
            task=task,
            file_list=file_list,
        )
        if repository_context:
            user_prompt += f"\n[REPOSITORY CONTEXT]\n{format_repository_context_for_prompt(repository_context)}"

        result = await client.chat(
            messages=[
                {"role": "system", "content": _PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=model_cfg.name,
            temperature=0.0,
            max_tokens=1024,
            num_ctx=model_cfg.num_ctx,
            timeout_seconds=model_cfg.timeout_seconds,
            allow_gpu=model_cfg.allow_gpu,
        )

        plan = _parse_plan(result.message, ordered_files)

        if not plan:
            error = "change_planner: LLM returned an empty or unparseable plan."
            emit_failure(run_context, "change_planner_node", error, start)
            return {"planner_error": error}

        emit_success(
            run_context,
            "change_planner_node",
            {"steps": len(plan), "files": [s["file"] for s in plan]},
            start,
        )
        return {"change_plan": plan}
    except Exception as exc:
        emit_failure(run_context, "change_planner_node", str(exc), start)
        raise


def _topological_order(files: list[str], repo_path: str | None) -> list[str]:
    """Order files so definition files precede their importers.

    Falls back to the original order when repo_path is unavailable or indexing fails.
    """
    if not repo_path:
        return list(files)
    try:
        indexer = AstIndexer()
        snapshot = indexer.build_snapshot(repo_path)

        # Build importer count for each file in the set: more importers = more downstream.
        file_set = set(files)
        importer_count: dict[str, int] = defaultdict(int)
        for edge in snapshot.edges:
            if edge.from_path in file_set and edge.to_path in file_set:
                importer_count[edge.to_path] += 1  # to_path is imported by from_path

        # Definition files have more importers; callers have fewer or none.
        # Sort descending so definitions come before callers.
        return sorted(files, key=lambda f: importer_count.get(f, 0), reverse=True)
    except Exception as exc:
        logger.warning("change_planner: topological sort failed (%s), using original order", exc)
        return list(files)


def _parse_plan(raw: str, valid_files: list[str]) -> list[dict]:
    """Parse LLM output into a list of valid ChangePlanStep dicts."""
    text = raw.strip()

    # Strip markdown fences if present.
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end]).strip()

    parsed: list[dict] = []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            parsed = data
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                logger.warning("change_planner: could not parse plan JSON: %r", raw[:300])
                return []

    # Validate, normalise, and deduplicate steps.
    # The LLM occasionally emits the same file more than once; keep only the
    # first occurrence so plan_dispatcher doesn't process the same file twice.
    valid_set = set(valid_files)
    seen_files: set[str] = set()
    result: list[dict] = []
    for step in parsed:
        if not isinstance(step, dict):
            continue
        file_path = step.get("file", "")
        if file_path not in valid_set:
            logger.warning("change_planner: skipping step with unknown file %r", file_path)
            continue
        if file_path in seen_files:
            logger.warning("change_planner: skipping duplicate step for file %r", file_path)
            continue
        seen_files.add(file_path)
        result.append(
            {
                "file": file_path,
                "operation": str(step.get("operation", "modify")),
                "symbol": str(step.get("symbol", "")),
                "change": str(step.get("change", "")),
                "reason": str(step.get("reason", "")),
            }
        )
    return result
