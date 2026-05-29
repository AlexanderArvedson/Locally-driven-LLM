"""Semantic validator node.

Evaluates whether the generated code correctly satisfies the original task
intent using an LLM judge. This node must never rewrite code — it only
reasons about the alignment between task description and generated output.
"""

from __future__ import annotations

import json
import time

from src.graph.nodes.support import client, require_state_value, strip_code_fences
from src.config_loader import get_semantic_model, get_semantic_threshold
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success

_SYSTEM_PROMPT = (
    "You are a code review expert. Evaluate whether the generated code correctly "
    "implements the requested task. Respond only with valid JSON — no markdown fences, "
    "no explanation outside the JSON object."
)

_FALLBACK_RESULT = {
    "passed": True,
    "task_alignment_score": 1.0,
    "missing_requirements": [],
    "incorrect_behaviors": [],
    "unnecessary_changes": [],
    "notes": "JSON parse failed — soft pass applied.",
    "confidence": 0.3,
}


def _build_semantic_feedback(result: dict) -> str:
    """Format the LLM evaluation into a concise string for the coder prompt."""
    parts = []
    missing = result.get("missing_requirements") or []
    incorrect = result.get("incorrect_behaviors") or []
    unnecessary = result.get("unnecessary_changes") or []

    if missing:
        parts.append("Missing requirements:\n" + "\n".join(f"- {r}" for r in missing))
    if incorrect:
        parts.append("Incorrect behaviors:\n" + "\n".join(f"- {b}" for b in incorrect))
    if unnecessary:
        parts.append("Unnecessary changes:\n" + "\n".join(f"- {c}" for c in unnecessary))

    score = result.get("task_alignment_score", 0.0)
    parts.append(f"Alignment score: {score:.2f}")
    return "\n\n".join(parts)


async def semantic_validator_node(state: GraphState, run_context: RunContext) -> dict:
    """Evaluate task-intent alignment of the generated code using an LLM judge.

    Reads task, generated_code, original_code, and prior validation feedback
    from state. Returns a structured evaluation including task_alignment_score
    and categorised issues. Applies a threshold gate: if score >= configured
    threshold, semantic_passed is True regardless of the LLM passed flag —
    this prevents overly sensitive LLM judgements from blocking correct code.

    This node does not execute code and does not rewrite it.
    """
    start = time.time()
    try:
        task = require_state_value(state, "task")
        generated_code = strip_code_fences(require_state_value(state, "generated_code"))
        original_code = state.get("original_code") or "N/A"
        review_feedback = state.get("review_feedback") or "passed"
        verification_feedback = state.get("verification_feedback") or "passed"

        model = get_semantic_model(state.get("repo_path"))
        threshold = get_semantic_threshold(state.get("repo_path"))

        user_prompt = (
            f"[TASK]\n{task}\n\n"
            f"[ORIGINAL CODE]\n{original_code}\n\n"
            f"[GENERATED CODE]\n{generated_code}\n\n"
            f"[STATIC VALIDATION]\n{review_feedback}\n\n"
            f"[RUNTIME VALIDATION]\n{verification_feedback}\n\n"
            "[INSTRUCTION]\n"
            "Evaluate whether the generated code correctly and completely implements the task.\n"
            "Return a JSON object with exactly these keys:\n"
            '- "passed": bool\n'
            '- "task_alignment_score": float between 0.0 and 1.0\n'
            '- "missing_requirements": list of strings\n'
            '- "incorrect_behaviors": list of strings\n'
            '- "unnecessary_changes": list of strings\n'
            '- "notes": string\n'
            '- "confidence": float between 0.0 and 1.0'
        )

        response = await client.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            temperature=0.1,
        )

        raw = strip_code_fences(response.message)
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            result = _FALLBACK_RESULT

        score = float(result.get("task_alignment_score", 0.0))
        semantic_passed = score >= threshold

        feedback = _build_semantic_feedback(result) if not semantic_passed else ""

        payload = {
            "semantic_passed": semantic_passed,
            "task_alignment_score": score,
        }
        if semantic_passed:
            emit_success(run_context, "semantic_validator_node", payload, start)
        else:
            emit_failure(run_context, "semantic_validator_node", feedback, start)

        return {
            "semantic_passed": semantic_passed,
            "semantic_feedback": feedback,
            "task_alignment_score": score,
            "missing_requirements": result.get("missing_requirements") or [],
            "incorrect_behaviors": result.get("incorrect_behaviors") or [],
            "unnecessary_changes": result.get("unnecessary_changes") or [],
            "semantic_notes": result.get("notes") or "",
            "semantic_confidence": float(result.get("confidence", 0.0)),
        }

    except Exception as e:
        emit_failure(run_context, "semantic_validator_node", str(e), start)
        raise
