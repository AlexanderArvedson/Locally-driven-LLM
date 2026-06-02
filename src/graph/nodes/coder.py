"""Coder node."""

from __future__ import annotations

import logging
import time

from src.config_loader import get_coder_model_config
from src.graph.nodes.support import client, require_state_value, strip_code_fences
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success
from src.retrieval.contracts.context_contract import format_repository_context_for_prompt
from src.retrieval.slicing import SymbolSlice, get_slicer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Symbol-mode prompt helpers
# ---------------------------------------------------------------------------

def _format_target_symbol(ctx: dict, target_file: str) -> str:
    fname = target_file.split("/")[-1] if target_file else ""
    parts = [f"[TARGET SYMBOL — {fname}]"]

    imports = (ctx.get("required_imports") or "").strip()
    if imports:
        parts.append(f"--- Required imports ---\n{imports}")

    class_ctx = ctx.get("class_context")
    if class_ctx:
        parts.append(f"--- Enclosing class ---\n{class_ctx}")

    symbol = ctx.get("target_symbol", "")
    src = ctx.get("target_source", "")
    if src:
        parts.append(f"--- Symbol: {symbol} ---\n{src.rstrip()}")

    return "\n\n".join(parts)


def _format_contracts(ctx: dict) -> str:
    contracts = (ctx.get("contracts") or "").strip()
    if not contracts:
        return ""
    return f"[CONTRACTS]\n{contracts}"


def _build_symbol_prompt(
    task: str,
    target_file: str,
    ctx: dict,
    failure_parts: list[str],
) -> str:
    symbol = ctx.get("target_symbol", "")
    fname = target_file.split("/")[-1] if target_file else "the file"

    sections = [
        f"[TASK]\n{task}",
        _format_target_symbol(ctx, target_file),
    ]
    contracts = _format_contracts(ctx)
    if contracts:
        sections.append(contracts)
    if failure_parts:
        sections.append("[VALIDATION FEEDBACK]\n" + "\n\n".join(failure_parts))

    sections.append(
        "[INSTRUCTION]\n"
        f"Modify the [{symbol}] symbol shown above to complete the task.\n"
        "Return ONLY the modified symbol — the complete definition including "
        "any decorators, the def/class header, docstring, and body.\n"
        f"Preserve the original indentation exactly (the symbol lives in {fname}).\n"
        "Do NOT include class definitions, other methods, imports, or any surrounding code.\n"
        "Do NOT wrap output in markdown code fences.\n"
        "Output should be ONLY the symbol source, ready to be spliced back into the file."
    )
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Full-file prompt helpers (fallback / no context slice)
# ---------------------------------------------------------------------------

def _format_related_files(related_file_contents: dict[str, str]) -> str:
    if not related_file_contents:
        return "[RELATED FILES]\n- none"
    lines = ["[RELATED FILES]"]
    for path, content in related_file_contents.items():
        lines.append(f"--- {path} ---\n{content}")
    return "\n\n".join(lines)


def _build_full_file_prompt(
    task: str,
    target_file: str,
    original_code: str,
    repository_context,
    related_file_contents: dict,
    failure_parts: list[str],
) -> str:
    prompt = (
        f"[TASK]\n{task}\n\n"
        f"[TARGET FILE]\n{target_file}\n\n"
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
    if failure_parts:
        prompt += (
            "\n\n"
            + "\n\n".join(failure_parts)
            + "\n\nRevise the code to address all issues above. "
            "Make only the minimal changes needed; preserve all unchanged lines exactly. "
            "Return the full updated file only."
        )
    return prompt


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def coder_node(state: GraphState, run_context: RunContext) -> dict:
    start = time.time()
    try:
        iteration = state.get("iteration", 0) + 1
        original_code = require_state_value(state, "original_code")
        repository_context = state.get("repository_context")
        model_cfg = get_coder_model_config(state.get("repo_path"))
        task = state.get("task", "")
        target_file = state.get("target_file", "")
        context_slice: dict | None = state.get("context_slice")

        # Build failure feedback regardless of prompt mode.
        failure_parts: list[str] = []

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

        # Choose prompt mode.
        use_slice = bool(context_slice and context_slice.get("target_source") is not None)

        if use_slice:
            user_prompt = _build_symbol_prompt(task, target_file, context_slice, failure_parts)  # type: ignore[arg-type]
            system_msg = (
                "You are an expert software engineer. "
                "Return only the requested symbol — no surrounding code, no markdown."
            )
        else:
            user_prompt = _build_full_file_prompt(
                task,
                target_file,
                original_code,
                repository_context,
                state.get("related_file_contents") or {},
                failure_parts,
            )
            system_msg = (
                "You are an expert software engineer. "
                "Generate clean, production-quality code."
            )

        result = await client.chat(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
            model=model_cfg.name,
            temperature=model_cfg.temperature,
            max_tokens=model_cfg.max_tokens,
            num_ctx=model_cfg.num_ctx,
            timeout_seconds=model_cfg.timeout_seconds,
            allow_gpu=model_cfg.allow_gpu,
        )

        if use_slice:
            assert context_slice is not None
            raw_output = strip_code_fences(result.message)
            slicer = get_slicer(target_file)
            if slicer is not None:
                sym_slice = SymbolSlice(
                    name=context_slice["target_symbol"],
                    source=context_slice["target_source"],
                    start_line=context_slice["symbol_start_line"],
                    end_line=context_slice["symbol_end_line"],
                    indent=context_slice["symbol_indent"],
                )
                stitched = slicer.stitch_symbol(original_code, sym_slice, raw_output)
                if stitched == original_code:
                    # Stitch found no matching lines — symbol may have moved.
                    # Treat LLM output as a full-file response so validation can surface it.
                    logger.warning(
                        "coder: stitch unchanged for symbol %r in %s; using raw output",
                        context_slice["target_symbol"],
                        target_file,
                    )
                    generated_code = raw_output
                else:
                    generated_code = stitched
            else:
                generated_code = raw_output
        else:
            # Full-file mode: file_writer_node handles fence stripping.
            generated_code = result.message

        emit_success(
            run_context,
            "coder_node",
            {"model": model_cfg.name, "slice_mode": use_slice},
            start,
        )

        return {
            "generated_code": generated_code,
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
