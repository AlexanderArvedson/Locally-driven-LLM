"""Shared helpers for graph node implementations."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from src.core.ollama_client import OllamaClient
from src.graph.state import GraphState
from src.config_loader import get_ollama_base_url, CODER_MODEL, MAX_ITERATIONS


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


client = OllamaClient(base_url=get_ollama_base_url())



def require_state_value(state: GraphState, key: str):
    """Return a required value from `state` or raise ValueError."""
    value = state.get(key)
    if value is None:
        raise ValueError(f"Missing required state value: {key}")
    return value


def strip_code_fences(content: str) -> str:
    """Remove a single pair of surrounding Markdown code fences."""
    lines = content.strip().splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip("\n")


def validate_python_syntax(content: str) -> tuple[bool, str]:
    """Validate that `content` compiles as Python."""
    if not content.strip():
        return False, "Generated code is empty."

    try:
        compile(content, "<generated_code>", "exec")
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno is not None else "an unknown line"
        return False, f"Generated code has a syntax error at {location}: {exc.msg}"

    return True, ""


def select_target_file_from_repo_path(repo_path: str) -> str:
    """Pick the first Python file in a repo root deterministically."""
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
