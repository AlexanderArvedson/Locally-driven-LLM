"""Coder node."""

from __future__ import annotations

import time

from src.graph.nodes.support import client, require_state_value
from src.config_loader import get_coder_model_config
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.contracts.context_contract import format_repository_context_for_prompt


def _format_related_files(related_file_contents: dict[str, str]) -> str:
    if not related_file_contents:
        return "[RELATED FILES]\n- none"
    lines = ["[RELATED FILES]"]
    for path, content in related_file_contents.items():
        lines.append(f"--- {path} ---\n{content}")
    return "\n\n".join(lines)


async def coder_node(state: GraphState, run_context: RunContext) -> dict:
    start = time.time()
    try:
        iteration = state.get("iteration", 0) + 1
        original_code = require_state_value(state, "original_code")
        repository_context = state.get("repository_context")
        model_cfg = get_coder_model_config(state.get("repo_path"))

        related_file_contents = state.get("related_file_contents", {})
        user_prompt = (
            f"[TASK]\n{state['task']}\n\n"
            f"[TARGET FILE]\n{state.get('target_file', '')}\n\n"
            f"[FILE CONTENT]\n{original_code}\n\n"
            f"{format_repository_context_for_prompt(repository_context)}\n\n"
            f"{_format_related_files(related_file_contents)}\n\n"
            "[INSTRUCTION]\n"
            "Only modify the target file.\n"
            "Make ONLY the minimal changes required to complete the task.\n"
            "Preserve all existing code structure, style, comments, imports, and formatting exactly.\n"
            "Do NOT reformat, reorder, rename, or rewrite any lines not directly required by the task.\n"
            "Use repository context and related files for reasoning only.\n"
            "Return the FULL updated file as plain text.\n"
            "Do NOT wrap your output in markdown code fences (```), backticks, or add any explanation.\n"
            "Output should be the literal file contents to write to disk."
        )
        failure_parts = []

        syntax_ok = state.get("syntax_ok", True)
        review_errors = state.get("review_errors") or []
        if not syntax_ok or review_errors:
            errors_str = (
                "\n".join(f"- {e}" for e in review_errors)
                if review_errors
                else state.get("review_feedback", "")
            )
            failure_parts.append(f"STATIC VALIDATION FAILED:\n{errors_str}")

        verification_feedback = state.get("verification_feedback", "")
        error_type = state.get("error_type")
        # ImportError means the sandbox lacks project-local packages — unfixable by
        # the coder. Passing it as feedback causes the model to return unchanged code.
        if verification_feedback and error_type != "ImportError":
            label = f"RUNTIME FAILURE ({error_type}):" if error_type else "RUNTIME FAILURE:"
            failure_parts.append(f"{label}\n{verification_feedback}")

        semantic_feedback = state.get("semantic_feedback", "")
        missing = state.get("missing_requirements") or []
        incorrect = state.get("incorrect_behaviors") or []
        if semantic_feedback or missing or incorrect:
            parts = ["TASK MISALIGNMENT:"]
            if missing:
                parts.append("Missing requirements:\n" + "\n".join(f"- {r}" for r in missing))
            if incorrect:
                parts.append("Incorrect behaviors:\n" + "\n".join(f"- {b}" for b in incorrect))
            failure_parts.append("\n".join(parts))

        if failure_parts:
            user_prompt = (
                f"{user_prompt}\n\n"
                + "\n\n".join(failure_parts)
                + "\n\nRevise the code to address all issues above. Make only the minimal changes needed; preserve all unchanged lines exactly. Return the full updated file only."
            )

        result = await client.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert software engineer. "
                        "Generate clean, production-quality code."
                    ),
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            model=model_cfg.name,
            temperature=model_cfg.temperature,
            max_tokens=model_cfg.max_tokens,
            num_ctx=model_cfg.num_ctx,
            timeout_seconds=model_cfg.timeout_seconds,
            allow_gpu=model_cfg.allow_gpu,
        )

        emit_success(run_context, "coder_node", {"model": model_cfg.name}, start)

        return {
            "generated_code": result.message,
            "iteration": iteration,
            "review_passed": False,
            "semantic_passed": False,
            "semantic_feedback": "",
            "missing_requirements": [],
            "incorrect_behaviors": [],
        }
    except Exception as e:
        emit_failure(run_context, "coder_node", str(e), start)
        raise
