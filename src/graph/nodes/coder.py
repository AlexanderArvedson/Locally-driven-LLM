"""Coder node."""

from __future__ import annotations

import time

from src.graph.nodes.support import client, require_state_value
from src.config_loader import get_coder_model
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.repository.context_contract import format_repository_context_for_prompt


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
        review_feedback = state.get("review_feedback")
        original_code = require_state_value(state, "original_code")
        repository_context = state.get("repository_context")
        coder_model = get_coder_model(state.get("repo_path"))

        related_file_contents = state.get("related_file_contents", {})
        user_prompt = (
            f"[TASK]\n{state['task']}\n\n"
            f"[TARGET FILE]\n{state.get('target_file', '')}\n\n"
            f"[FILE CONTENT]\n{original_code}\n\n"
            f"{format_repository_context_for_prompt(repository_context)}\n\n"
            f"{_format_related_files(related_file_contents)}\n\n"
            "[INSTRUCTION]\n"
            "Only modify the target file.\n"
            "Use repository context and related files for reasoning only.\n"
            "Return the FULL updated file only as plain text.\n"
            "Do NOT wrap your output in markdown code fences (```), backticks, or add any explanation.\n"
            "Output should be the literal file contents to write to disk."
        )
        if review_feedback:
            user_prompt = (
                f"{user_prompt}\n\n"
                f"Previous review feedback: {review_feedback}\n"
                "Revise the code to address the feedback while still returning the full updated file only."
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
            model=coder_model,
            temperature=0.2,
        )

        emit_success(run_context, "coder_node", state.get("task", ""), {"model": coder_model}, start)

        return {
            "generated_code": result.message,
            "iteration": iteration,
            "review_passed": False,
        }
    except Exception as e:
        emit_failure(run_context, "coder_node", state.get("task", ""), str(e), start)
        raise
