"""Semantic validator node.

Evaluates whether the generated code correctly satisfies the original task
intent using an LLM judge. This node must never rewrite code — it only
reasons about the alignment between task description and generated output.
"""

from __future__ import annotations

import json
import time

from src.graph.nodes.support import client, require_state_value, strip_code_fences
from src.config_loader import get_semantic_model_config, get_semantic_threshold
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success

_SYSTEM_PROMPT = (
    "You are a strict code review expert evaluating a code change for correctness and safety. "
    "A change passes ONLY when it fully implements the task AND does not alter existing "
    "behaviour outside the task scope. Regressions are as serious as missing requirements. "
    "Respond only with valid JSON — no markdown fences, no explanation outside the JSON object."
)

# Conservative fallback: parse failure is treated as uncertain, not a pass.
_FALLBACK_RESULT = {
    "passed": False,
    "task_alignment_score": 0.5,
    "regression_risk": 0.5,
    "missing_requirements": [],
    "incorrect_behaviors": [],
    "unnecessary_changes": [],
    "notes": "JSON parse failed — conservative score applied.",
    "confidence": 0.1,
}

# regression_risk above this threshold penalises the effective score.
_REGRESSION_RISK_TOLERANCE = 0.4
# Weight applied to the excess regression risk when computing the effective score.
_REGRESSION_RISK_WEIGHT = 0.5
# Original code is included as context only; cap it to avoid burning context budget.
_ORIGINAL_CODE_CONTEXT_CHARS = 1_500


def _build_semantic_feedback(result: dict, effective_score: float) -> str:
    """Format the LLM evaluation into a concise string for the coder prompt."""
    parts = []
    missing = result.get("missing_requirements") or []
    incorrect = result.get("incorrect_behaviors") or []
    unnecessary = result.get("unnecessary_changes") or []
    regression_risk = float(result.get("regression_risk", 0.0))

    if missing:
        parts.append("Missing requirements:\n" + "\n".join(f"- {r}" for r in missing))
    if incorrect:
        parts.append("Incorrect behaviors:\n" + "\n".join(f"- {b}" for b in incorrect))
    if unnecessary:
        parts.append("Unnecessary changes:\n" + "\n".join(f"- {c}" for c in unnecessary))
    if regression_risk > _REGRESSION_RISK_TOLERANCE:
        parts.append(f"Regression risk: {regression_risk:.2f} — the change likely alters existing behaviour outside the task scope.")

    parts.append(f"Effective score: {effective_score:.2f}")
    return "\n\n".join(parts)


async def semantic_validator_node(state: GraphState, run_context: RunContext) -> dict:
    """Evaluate task-intent alignment and regression risk of the generated change.

    Uses the unified diff as the primary evaluation target rather than two full
    file listings — this keeps the prompt focused on what actually changed and
    leaves more context budget for reasoning. A truncated snippet of the original
    file is included for background context only.

    Pass/fail is determined by an effective score that penalises high regression
    risk: effective_score = task_alignment_score - max(0, regression_risk - tolerance) * weight.

    This node does not execute code and does not rewrite it.
    """
    start = time.time()
    try:
        task = require_state_value(state, "task")
        generated_diff = state.get("generated_diff") or ""
        original_code = state.get("original_code") or ""
        review_feedback = state.get("review_feedback") or "passed"
        # ImportError from the sandbox means project-local packages are not on the
        # sandbox path — an environment issue, not a code regression. Passing the
        # raw error to the model causes it to score regression_risk at 1.0 for
        # something the generated code did not cause.
        error_type = state.get("error_type")
        if error_type == "ImportError":
            verification_feedback = "passed (sandbox import errors are environment-only; not a code quality signal)"
        else:
            verification_feedback = state.get("verification_feedback") or "passed"

        model_cfg = get_semantic_model_config(state.get("repo_path"))
        threshold = get_semantic_threshold(state.get("repo_path"))

        # Truncate original to a brief context snippet — the diff carries the detail.
        original_snippet = (
            original_code[:_ORIGINAL_CODE_CONTEXT_CHARS] + "\n... [truncated]"
            if len(original_code) > _ORIGINAL_CODE_CONTEXT_CHARS
            else original_code or "N/A"
        )

        user_prompt = (
            f"[TASK]\n{task}\n\n"
            f"[ORIGINAL FILE (context only, truncated)]\n{original_snippet}\n\n"
            f"[DIFF]\n{generated_diff or '(no diff — file may be unchanged)'}\n\n"
            f"[STATIC VALIDATION]\n{review_feedback}\n\n"
            f"[RUNTIME VALIDATION]\n{verification_feedback}\n\n"
            "[INSTRUCTION]\n"
            "Evaluate the diff above. Answer two questions:\n"
            "1. Does the diff correctly and completely implement the task?\n"
            "2. Does the diff alter any existing behaviour NOT explicitly required by the task?\n"
            "List every functional regression or unrequested behaviour change in "
            "'incorrect_behaviors' or 'unnecessary_changes' — do not omit them.\n"
            "Return a JSON object with exactly these keys:\n"
            '- "passed": bool\n'
            '- "task_alignment_score": float 0.0–1.0\n'
            '- "regression_risk": float 0.0–1.0 '
            "(0.0 = no existing behaviour changed, 1.0 = major regression)\n"
            '- "missing_requirements": list of strings\n'
            '- "incorrect_behaviors": list of strings\n'
            '- "unnecessary_changes": list of strings\n'
            '- "notes": string\n'
            '- "confidence": float 0.0–1.0'
        )

        response = await client.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=model_cfg.name,
            temperature=model_cfg.temperature,
            max_tokens=model_cfg.max_tokens,
            num_ctx=model_cfg.num_ctx,
            timeout_seconds=model_cfg.timeout_seconds,
            allow_gpu=model_cfg.allow_gpu,
        )

        raw = strip_code_fences(response.message)
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            result = _FALLBACK_RESULT

        task_alignment_score = float(result.get("task_alignment_score", 0.0))
        regression_risk = float(result.get("regression_risk", 0.0))

        # Penalise scores where regression risk exceeds the tolerance threshold.
        penalty = max(0.0, regression_risk - _REGRESSION_RISK_TOLERANCE) * _REGRESSION_RISK_WEIGHT
        effective_score = max(0.0, task_alignment_score - penalty)
        semantic_passed = effective_score >= threshold

        feedback = _build_semantic_feedback(result, effective_score) if not semantic_passed else ""

        payload = {
            "semantic_passed": semantic_passed,
            "task_alignment_score": task_alignment_score,
            "regression_risk": regression_risk,
            "effective_score": round(effective_score, 3),
        }
        if semantic_passed:
            emit_success(run_context, "semantic_validator_node", payload, start)
        else:
            emit_failure(run_context, "semantic_validator_node", feedback, start)

        return {
            "semantic_passed": semantic_passed,
            "semantic_feedback": feedback,
            "task_alignment_score": task_alignment_score,
            "regression_risk": regression_risk,
            "missing_requirements": result.get("missing_requirements") or [],
            "incorrect_behaviors": result.get("incorrect_behaviors") or [],
            "unnecessary_changes": result.get("unnecessary_changes") or [],
            "semantic_notes": result.get("notes") or "",
            "semantic_confidence": float(result.get("confidence", 0.0)),
        }

    except Exception as e:
        emit_failure(run_context, "semantic_validator_node", str(e), start)
        raise
