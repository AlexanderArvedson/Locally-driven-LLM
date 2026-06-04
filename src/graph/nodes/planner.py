"""Planner node — selects which file(s) to modify from retrieval candidates.

When ``target_file`` is already set in state (user-provided), the planner is
a no-op and simply records ``target_files = [target_file]``.

When ``target_file`` is absent the node asks the LLM to pick 1–3 files from
the retrieval-ranked ``selected_file_ids``. If the LLM decides none of the
candidates need modification, the run terminates with a ``planner_error``
rather than guessing or creating new files.
"""

from __future__ import annotations

import json
import logging
import re
import time

from src.core.config_loader import get_coder_model_config, get_planner_config
from src.graph.nodes.support import client
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.contracts.context_contract import format_repository_context_for_prompt

logger = logging.getLogger(__name__)


async def planner_node(state: GraphState, run_context: RunContext) -> dict:
    """Select the file(s) to modify for the current task.

    State inputs consumed:
      target_file (optional), selected_file_ids, task, repo_path

    State delta returned:
      target_file, target_files          — on success
      planner_error                      — when no file fits (run terminates)
    """
    start = time.time()
    try:
        # Respect an explicit caller-supplied target; skip LLM selection.
        if state.get("target_file"):
            target = state["target_file"]
            emit_success(run_context, "planner_node", {"skipped": True, "target_file": target}, start)
            return {"target_files": [target]}

        task = state.get("task", "")
        candidates = state.get("selected_file_ids", [])
        repo_path = state.get("repo_path")
        max_files = get_planner_config(repo_path).max_files

        if not candidates:
            error = "Planner: retrieval returned no candidate files to choose from."
            emit_failure(run_context, "planner_node", error, start)
            return {"planner_error": error}

        model_cfg = get_coder_model_config(repo_path)
        candidate_list = "\n".join(f"- {f}" for f in candidates)
        repository_context = state.get("repository_context")

        user_prompt = (
            f"[TASK]\n{task}\n\n"
            f"[CANDIDATE FILES]\n{candidate_list}\n\n"
            f"{format_repository_context_for_prompt(repository_context)}\n\n"
            "[INSTRUCTION]\n"
            "Select the files from the list above that must be MODIFIED to complete the task.\n"
            "Do NOT select files that are only needed for reading context.\n"
            f"Select at most {max_files} files.\n"
            "If no file in the list needs modification, use an empty array for 'files'.\n"
            "Also identify the single function, method, or class name that must be changed "
            "to complete the task (leave 'symbol' empty if the change spans the whole file "
            "or if you are unsure).\n"
            "Return ONLY a JSON object with this exact shape — no explanation, no markdown:\n"
            '{"files": ["src/foo.py"], "symbol": "my_function"}'
        )

        result = await client.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a code planning assistant. Respond only with a valid JSON object.",
                },
                {"role": "user", "content": user_prompt},
            ],
            model=model_cfg.name,
            temperature=0.0,
            max_tokens=256,
            num_ctx=model_cfg.num_ctx,
            timeout_seconds=model_cfg.timeout_seconds,
            allow_gpu=model_cfg.allow_gpu,
        )

        chosen, target_symbol = _parse_planner_response(result.message, candidates)
        chosen = chosen[:max_files]

        if not chosen:
            error = (
                f"Planner found no files to modify for task: {task!r}. "
                "Ensure the task describes a change to an existing file in the repository."
            )
            emit_failure(run_context, "planner_node", error, start)
            return {"planner_error": error}

        # selected_file_ids are repo-relative; resolve to absolute paths so that
        # downstream nodes (file_reader, file_writer) can open them directly.
        chosen = _resolve_paths(chosen, repo_path)

        emit_success(
            run_context,
            "planner_node",
            {"chosen_files": chosen, "target_symbol": target_symbol or None},
            start,
        )
        delta: dict = {"target_file": chosen[0], "target_files": chosen}
        if target_symbol:
            delta["target_symbol"] = target_symbol
        return delta
    except Exception as exc:
        emit_failure(run_context, "planner_node", str(exc), start)
        raise


def _resolve_paths(paths: list[str], repo_path: str | None) -> list[str]:
    """Convert repo-relative paths to absolute paths using repo_path as the root.

    Paths that are already absolute are returned unchanged.
    """
    if not repo_path:
        return paths
    from pathlib import Path as _Path
    root = _Path(repo_path)
    result = []
    for p in paths:
        pp = _Path(p)
        result.append(str(pp) if pp.is_absolute() else str(root / pp))
    return result


def _parse_planner_response(raw: str, valid_candidates: list[str]) -> tuple[list[str], str | None]:
    """Parse the planner LLM response into (chosen_files, target_symbol).

    Accepts the new ``{"files": [...], "symbol": "..."}`` shape.
    Falls back to a bare JSON array for backwards compatibility with prompts
    that may still return one.
    """
    text = raw.strip()

    # Strip markdown code fences if present.
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end]).strip()

    chosen: list[str] = []
    symbol: str | None = None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            files = parsed.get("files", [])
            if isinstance(files, list):
                chosen = [str(p) for p in files]
            raw_symbol = parsed.get("symbol", "")
            symbol = str(raw_symbol).strip() if raw_symbol else None
        elif isinstance(parsed, list):
            # Backwards-compatible bare array.
            chosen = [str(p) for p in parsed]
    except json.JSONDecodeError:
        # Fallback: find the first {...} block.
        m = re.search(r"\{[^}]*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                files = parsed.get("files", [])
                chosen = [str(p) for p in files] if isinstance(files, list) else []
                raw_symbol = parsed.get("symbol", "")
                symbol = str(raw_symbol).strip() if raw_symbol else None
            except json.JSONDecodeError:
                pass
        if not chosen:
            # Last resort: find the first [...] block.
            m2 = re.search(r"\[([^\]]*)\]", text, re.DOTALL)
            if m2:
                try:
                    chosen = json.loads(f"[{m2.group(1)}]")
                except json.JSONDecodeError:
                    logger.warning("planner_node: could not parse LLM response: %r", raw[:200])

    # Guard against hallucinated paths — only keep known candidates.
    candidate_set = set(valid_candidates)
    return [f for f in chosen if f in candidate_set], symbol or None
