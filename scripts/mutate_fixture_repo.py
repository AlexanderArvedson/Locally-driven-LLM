"""Run the workflow against the synthetic fixture repository and write the change in place.

This script is intentionally separate from the CI test helpers. It is meant for
manual experimentation with a local Ollama model against `sample_repo_v2`.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.graph.workflow import make_graph  # noqa: E402
from src.observability.context import RunContext  # noqa: E402


DEFAULT_REPO_PATH = PROJECT_ROOT / "tests" / "fixtures" / "sample_repo_v2"
DEFAULT_TARGET_FILE = DEFAULT_REPO_PATH / "app" / "processing" / "task_runner.py"
DEFAULT_TASK = (
    "Refactor the task pipeline to simplify validation and reporting while keeping "
    "the output and behavior stable."
)


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


async def _run(repo_path: Path, target_file: Path, task: str) -> dict[str, object]:
    run_context = RunContext.new()
    graph = make_graph(run_context)
    return await graph.ainvoke(
        {
            "task": task,
            "repo_path": str(repo_path),
            "target_file": str(target_file),
        }
    )


def main() -> int:
    repo_path = _resolve_path(os.getenv("FIXTURE_REPO_PATH"), DEFAULT_REPO_PATH)
    target_file = _resolve_path(os.getenv("FIXTURE_TARGET_FILE"), DEFAULT_TARGET_FILE)
    task = os.getenv("FIXTURE_TASK", DEFAULT_TASK)

    if not repo_path.exists():
        print(f"Repository path does not exist: {repo_path}")
        return 1
    if not target_file.exists():
        print(f"Target file does not exist: {target_file}")
        return 1

    before = target_file.read_text(encoding="utf-8")
    print(f"Repo: {repo_path}")
    print(f"Target: {target_file}")
    print(f"Model: {os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b')}")
    print(f"Task: {task}")
    print("--- BEFORE ---")
    print(before)

    result = asyncio.run(_run(repo_path, target_file, task))

    after = target_file.read_text(encoding="utf-8")
    print("--- AFTER ---")
    print(after)
    print("--- RESULT ---")
    print(result)
    print(f"CHANGED: {before != after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())