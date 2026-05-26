"""Node implementations for the LangGraph file-edit workflow.

Each node is an async function that accepts the shared `GraphState` and a
`RunContext` for observability. Nodes return small dictionaries of values to
be merged into state by the graph runtime. Nodes are responsible for their own
error handling and must emit a single JSONL event via the observability logger
on success or failure.
"""

from src.core.ollama_client import OllamaClient
from src.graph.state import GraphState
from src.tools.files import read_file, write_file
from src.tools.patches import generate_unified, apply_unified
from pathlib import Path
import os
from src.core.runtime_paths import FAILED_PATCHES_DIR, ensure_runtime_dirs
import logging
import subprocess
import tempfile
import shutil
import time

from src.observability.context import RunContext
from src.observability.logger import log_event
from src.observability.event_logging_utils import emit_success, emit_failure
from src.repository.simple_repository_indexer import SimpleRepositoryIndexer
from src.repository.retrieval_engine import SimpleRetrievalEngine
from src.repository.context_builder import SimpleContextBuilder
from src.repository.context_contract import (
    build_repository_context_payload,
    format_repository_context_for_prompt,
)


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


client = OllamaClient(base_url="http://localhost:11434")
MAX_ITERATIONS = 3


def _select_target_file_from_repo_path(repo_path: str) -> str:
    """Pick the first Python file in a repo root deterministically.

    If `repo_path` points at a file, that path is returned. If it points at a
    directory, the first `.py` file found by sorted recursive walk is returned.
    """
    repo_path = str(Path(repo_path))
    repo = Path(repo_path)
    if repo.is_file():
        return str(repo)

    if not repo.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    candidates: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = sorted(dirnames)
        for fname in sorted(filenames):
            if fname.endswith(".py"):
                candidates.append(os.path.normpath(os.path.join(dirpath, fname)))

    if not candidates:
        raise FileNotFoundError(f"No Python files found under repository path: {repo_path}")

    return candidates[0]


# Helper function to extract a required value from the graph state, raising an error if it's missing.
def _require_state_value(state: GraphState, key: str) -> str:
    """Return a required value from the graph `state` or raise ValueError.

    This helper centralizes the check for required state keys so node logic can
    assume presence after calling this function.

    Args:
        state: The shared GraphState mapping.
        key: The required key to extract.

    Returns:
        The value associated with `key`.

    Raises:
        ValueError: if the key is not present in `state`.
    """
    value = state.get(key)
    if value is None:
        raise ValueError(f"Missing required state value: {key}")

    return value

# Helper function to strip markdown code fences from the generated code, if present.
def _strip_code_fences(content: str) -> str:
    """Remove leading/trailing Markdown code fences from `content`.

    Many LLM responses may wrap code in triple-backtick fences. This helper
    strips a single leading and trailing fence pair if present and returns
    the trimmed code string.
    """
    lines = content.strip().splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip("\n")


# Helper function to validate that the generated code is syntactically correct Python. 
# Returns a tuple of (passed: bool, feedback: str).
def _validate_python_syntax(content: str) -> tuple[bool, str]:
    """Quickly validate Python syntax for the provided `content`.

    Returns a tuple `(passed, feedback)`. `passed` is `True` when the code
    compiles; otherwise `False` and `feedback` contains a short description of
    the syntax error.
    """
    if not content.strip():
        return False, "Generated code is empty."

    try:
        compile(content, "<generated_code>", "exec")
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno is not None else "an unknown line"
        return False, f"Generated code has a syntax error at {location}: {exc.msg}"

    return True, ""


# Takes the target file path from the state, reads its content, and returns it in a dictionary.
# This node is responsible for loading the original code that will be modified by the coder node.
async def file_reader_node(state: GraphState, run_context: RunContext) -> dict:
    """Read the target file specified in `state` and return its content.

    Emits a JSONL observability event recording success or failure. Returns a
    mapping with the key `original_code` containing the file contents.

    Args:
        state: GraphState with at least `target_file` set.
        run_context: RunContext used for observability.

    Returns:
        dict with `original_code` on success.
    """
    start = time.time()
    try:
        target_file = state.get("target_file")
        if not target_file:
            repo_path = _require_state_value(state, "repo_path")
            target_file = _select_target_file_from_repo_path(repo_path)

        original = read_file(target_file)

        emit_success(run_context, "file_reader_node", state.get("task", ""), {"original_length": len(original), "target_file": target_file}, start)

        return {"original_code": original, "target_file": target_file}
    except Exception as e:
        emit_failure(run_context, "file_reader_node", state.get("task", ""), str(e), start)
        raise


async def context_builder_node(state: GraphState, run_context: RunContext) -> dict:
    """Build a bounded repository ContextPackage for downstream nodes.

    Behavior:
    - Create a per-run RepositorySnapshot once and store it in `state['repository_snapshot']`.
    - Use the `SimpleRetrievalEngine` to select relevant files.
    - Use the `SimpleContextBuilder` to build a bounded `ContextPackage` and store it
      in `state['repository_context']`.

    Emits a success event with selected files and counts, or a failure event on error.
    """
    start = time.time()
    task = state.get("task", "")
    try:
        target_file = state.get("target_file")
        repo_path = state.get("repo_path")

        # Build snapshot once per execution and cache in state
        snapshot = state.get("repository_snapshot")
        if snapshot is None:
            indexer = SimpleRepositoryIndexer()
            snapshot_root = repo_path or (str(Path(target_file).parent) if target_file else ".")
            snapshot = indexer.build_snapshot(snapshot_root)
            # store snapshot for downstream nodes (keeps index lifecycle per-run)
            state["repository_snapshot"] = snapshot

        # Deterministic retrieval
        retriever = SimpleRetrievalEngine()
        selected = retriever.select_files(task, snapshot, target_file=target_file, max_files=15)

        # Build bounded context package
        builder = SimpleContextBuilder()
        context_pkg = builder.build_context(task, target_file, selected, snapshot, max_files=15)

        serialized = build_repository_context_payload(context_pkg, selected, repo_path=repo_path)

        # Store package in state for later nodes (coder, reviewer)
        state["repository_context"] = serialized

        payload = {
            "selected_files": selected,
            "num_selected": len(selected),
            "total_symbols": context_pkg.total_symbols,
        }
        emit_success(run_context, "context_builder_node", task, payload, start)

        return {"repository_context": serialized}
    except Exception as e:
        emit_failure(run_context, "context_builder_node", task, str(e), start)
        raise


# Takes the generated code from the state and writes it back to the target file.
# This node is responsible for saving the modifications made by the coder node to the filesystem.
async def file_writer_node(state: GraphState, run_context: RunContext) -> dict:
    """Write generated code back to the target file or apply a generated diff.

    If a `generated_diff` exists in `state`, it's applied atomically; otherwise
    the full `generated_code` is written. On error, artifacts are persisted to
    `failed_patches/` and a failure observability event is emitted.

    Args:
        state: GraphState containing `target_file` and `generated_code` or `generated_diff`.
        run_context: RunContext used for observability.

    Returns:
        dict with `updated_code` on success, or a dict describing verification failure.
    """
    start = time.time()
    try:
        target_file = _require_state_value(state, "target_file")
        generated_code = _strip_code_fences(_require_state_value(state, "generated_code"))
        # If a diff was provided, apply it; otherwise write the full file.
        if state.get("generated_diff"):
            try:
                apply_unified(target_file, _require_state_value(state, "generated_diff"))
            except Exception as exc:
                # Abort and surface error: do not overwrite the file. Persist failed patch for manual inspection.
                ensure_runtime_dirs()
                failed_path = FAILED_PATCHES_DIR / (Path(target_file).name + ".failed.patch")
                try:
                    failed_path.write_text(_require_state_value(state, "generated_diff"), encoding="utf-8")
                except Exception as wexc:
                    logger.error("Failed to write failed patch file: %s", wexc)

                logger.error("Applying unified diff failed for %s: %s; saved to %s", target_file, exc, failed_path)

                emit_failure(run_context, "file_writer_node", state.get("task", ""), str(exc), start)

                return {
                    "verification_passed": False,
                    "verification_feedback": f"Applying unified diff failed: {exc}; saved failed patch at {failed_path}",
                }
        else:
            try:
                write_file(target_file, generated_code)
            except Exception as exc:
                # Persist the generated code for manual inspection
                ensure_runtime_dirs()
                failed_path = FAILED_PATCHES_DIR / (Path(target_file).name + ".failed.py")
                try:
                    failed_path.write_text(generated_code, encoding="utf-8")
                except Exception as wexc:
                    logger.error("Failed to write failed generated file: %s", wexc)

                logger.error("Writing file failed for %s: %s; saved to %s", target_file, exc, failed_path)
                emit_failure(run_context, "file_writer_node", state.get("task", ""), str(exc), start)

                return {
                    "verification_passed": False,
                    "verification_feedback": f"Writing file failed: {exc}; saved generated output at {failed_path}",
                }

        emit_success(run_context, "file_writer_node", state.get("task", ""), {"updated_length": len(generated_code)}, start)

        return {"updated_code": generated_code}
    except Exception as e:
        emit_failure(run_context, "file_writer_node", state.get("task", ""), str(e), start)
        raise


# This node generate code based on the task, original code, and any review feedback.
# It constructs a prompt for the LLM and calls the Ollama client to get the modified code.
async def coder_node(state: GraphState, run_context: RunContext) -> dict:
    """Generate updated file contents using the configured LLM client.

    Constructs a prompt using the task and original file contents, calls the
    LLM via `client.chat`, and returns `generated_code` along with updated
    iteration metadata. Emits a success/failure observability event.

    Args:
        state: GraphState with `task` and `original_code`.
        run_context: RunContext used for observability.

    Returns:
        dict containing `generated_code`, `iteration`, and `review_passed`.
    """
    start = time.time()
    try:
        iteration = state.get("iteration", 0) + 1
        review_feedback = state.get("review_feedback")
        original_code = _require_state_value(state, "original_code")
        repository_context = state.get("repository_context")

        user_prompt = (
            f"[TASK]\n{state['task']}\n\n"
            f"[TARGET FILE]\n{state.get('target_file', '')}\n\n"
            f"[FILE CONTENT]\n{original_code}\n\n"
            f"{format_repository_context_for_prompt(repository_context)}\n\n"
            "[INSTRUCTION]\n"
            "Only modify the target file.\n"
            "Use repository context for reasoning only.\n"
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
            model="qwen2.5-coder:7b",
            temperature=0.2,
        )

        emit_success(run_context, "coder_node", state.get("task", ""), {"model": "qwen2.5-coder:7b"}, start)

        return {
            "generated_code": result.message,
            "iteration": iteration,
            "review_passed": False,
        }
    except Exception as e:
        emit_failure(run_context, "coder_node", state.get("task", ""), str(e), start)
        raise


# This node reviews the generated code using simple heuristics to determine if it meets basic quality standards.
async def reviewer_node(state: GraphState, run_context: RunContext) -> dict:
    """Review generated code using syntax checks and optional `ruff` linting.

    Performs a syntax validation and, if available, runs `ruff` against a
    temporary file. Emits observability events describing pass/fail and
    returns a mapping with `review_passed` and optional `review_feedback`.

    Args:
        state: GraphState expected to contain `generated_code`.
        run_context: RunContext used for observability.

    Returns:
        dict with `review_passed` and `review_feedback`.
    """
    start = time.time()
    try:
        code = _strip_code_fences(_require_state_value(state, "generated_code"))
        passed, feedback = _validate_python_syntax(code)

        if not passed:
            emit_failure(run_context, "reviewer_node", state.get("task", ""), feedback, start)
            return {"review_passed": False, "review_feedback": feedback}

        # Prefer running `ruff` for linting if available. We write the generated code
        # to a temporary file and run ruff on it. If ruff reports issues, fail review.
        if shutil.which("ruff"):
            tf = None
            tf_name = None
            try:
                tf = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
                tf.write(code)
                tf.flush()
                tf_name = tf.name
                tf.close()

                # Ruff v0.1+ uses subcommands; `check` keeps behavior explicit.
                res = subprocess.run(["ruff", "check", tf_name], capture_output=True, text=True)
                if res.returncode != 0:
                    # ruff found issues — include stdout/stderr in feedback
                    out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
                    emit_failure(run_context, "reviewer_node", state.get("task", ""), out, start)
                    return {"review_passed": False, "review_feedback": f"Ruff reported issues:\n{out}"}
            except FileNotFoundError:
                # ruff disappeared between check and run; fall back to heuristics below
                pass
            finally:
                try:
                    if tf_name is not None and Path(tf_name).exists():
                        Path(tf_name).unlink()
                except Exception:
                    pass

        # Fallback heuristics if ruff isn't available: basic quality checks.
        heur_pass = (
            "def " in code
            and "TODO" not in code
            and len(code) > 20
        )
        if not heur_pass:
            emit_failure(run_context, "reviewer_node", state.get("task", ""), "Heuristic checks failed", start)
            return {"review_passed": False, "review_feedback": "Heuristic checks failed: ensure function definitions exist, avoid TODO markers, and file is non-trivial."}

        emit_success(run_context, "reviewer_node", state.get("task", ""), {"review_passed": True}, start)

        return {"review_passed": True, "review_feedback": ""}
    except Exception as e:
        emit_failure(run_context, "reviewer_node", state.get("task", ""), str(e), start)
        raise


# This node performs a final verification step by executing the generated code in an isolated namespace to catch any runtime errors.
async def verifier_node(state: GraphState, run_context: RunContext) -> dict:
    """Run a lightweight verification of the generated code by executing it.

    Ensures the generated code compiles and can be executed safely in an
    isolated namespace. Optionally performs a trivial smoke test if an `add`
    function is present. Emits observability events and returns verification
    results.

    Args:
        state: GraphState containing `generated_code`.
        run_context: RunContext used for observability.

    Returns:
        dict with `verification_passed` and `verification_feedback`.
    """
    start = time.time()
    try:
        code = _strip_code_fences(_require_state_value(state, "generated_code"))

        # First, ensure syntax is valid (should already be true after reviewer)
        passed, feedback = _validate_python_syntax(code)
        if not passed:
            event = {
                "run_id": run_context.run_id,
                "node": "verifier_node",
                "status": "failure",
                "duration_ms": int((time.time() - start) * 1000),
                "task": state.get("task", ""),
                "payload": {"error": feedback},
            }
            log_event(run_context.run_id, event)
            return {"verification_passed": False, "verification_feedback": feedback}

        # Run the code in an isolated namespace to catch runtime errors on import/definition
        ns: dict = {}
        try:
            exec(code, ns)
        except Exception as exc:
            emit_failure(run_context, "verifier_node", state.get("task", ""), str(exc), start)
            return {"verification_passed": False, "verification_feedback": f"Runtime exec error: {exc}"}

        # Optional smoke test: if a function named `add` exists, call it once.
        if "add" in ns and callable(ns["add"]):
            try:
                ns["add"](1, 2)
            except Exception as exc:
                emit_failure(run_context, "verifier_node", state.get("task", ""), str(exc), start)
                return {"verification_passed": False, "verification_feedback": f"Runtime test failed: {exc}"}

        emit_success(run_context, "verifier_node", state.get("task", ""), {"verification_passed": True}, start)

        return {"verification_passed": True, "verification_feedback": ""}
    except Exception as e:
        emit_failure(run_context, "verifier_node", state.get("task", ""), str(e), start)
        raise


# This node generates a diff between the original code and the generated code using the ndiff format.
async def diff_generator_node(state: GraphState, run_context: RunContext) -> dict:
    """Produce a unified diff between the original and generated code.

    Uses `generate_unified` from `src.tools.patches` and emits a small
    observability event describing the diff size.

    Args:
        state: GraphState with `original_code` and `generated_code`.
        run_context: RunContext used for observability.

    Returns:
        dict with `generated_diff` on success.
    """
    start = time.time()
    try:
        original = _require_state_value(state, "original_code")
        generated = _strip_code_fences(_require_state_value(state, "generated_code"))
        nd = generate_unified(original, generated, fromfile=str(state.get("target_file", "a")), tofile=str(state.get("target_file", "b")))

        emit_success(run_context, "diff_generator_node", state.get("task", ""), {"diff_length": len(nd)}, start)

        return {"generated_diff": nd}
    except Exception as e:
        emit_failure(run_context, "diff_generator_node", state.get("task", ""), str(e), start)
        raise
