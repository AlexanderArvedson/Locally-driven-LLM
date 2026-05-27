"""Stress the scheduler with multiple mutation tasks against one fixture file.

This script starts the real async scheduler loop, enqueues three active tasks
with different prompts, and uses the local Ollama-backed workflow executor to
mutate the same target file in a short burst.

By default it copies the fixture repository into a temporary working directory
so the original fixtures stay clean. Pass `--in-place` if you want to mutate
the fixture repo directly.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scheduler.executor import WorkflowExecutor  # noqa: E402
from src.scheduler.loop import ExecutionLoop  # noqa: E402
from src.scheduler.queue import TaskQueue  # noqa: E402
from src.scheduler.task import Task  # noqa: E402


DEFAULT_REPO_PATH = PROJECT_ROOT / "tests" / "fixtures" / "sample_repo_v2"
DEFAULT_TARGET_FILE = Path("app/processing/task_runner.py")
DEFAULT_PROMPTS = [
    "Refactor the task pipeline to remove duplicated validation while keeping behavior stable.",
    "Tighten the implementation around the same task pipeline so the file is easier to maintain.",
    "Make a small structural improvement to the same file without changing the user-facing behavior.",
]


class ObservingWorkflowExecutor(WorkflowExecutor):
    def __init__(self) -> None:
        super().__init__()
        self.start_log: list[str] = []
        self.end_log: list[str] = []
        self.results: dict[str, object] = {}
        self.errors: dict[str, BaseException] = {}
        self.started_events: dict[str, asyncio.Event] = {}
        self.finished_events: dict[str, asyncio.Event] = {}

    def register(self, task_id: str) -> None:
        self.started_events[task_id] = asyncio.Event()
        self.finished_events[task_id] = asyncio.Event()

    async def execute(self, task: Task):
        self.start_log.append(task.id)
        if task.id in self.started_events:
            self.started_events[task.id].set()

        try:
            result = await super().execute(task)
            self.results[task.id] = result
            return result
        except BaseException as exc:  # pragma: no cover - manual debug aid
            self.errors[task.id] = exc
            raise
        finally:
            self.end_log.append(task.id)
            if task.id in self.finished_events:
                self.finished_events[task.id].set()


def _resolve_path(value: str | None, base: Path) -> Path:
    if not value:
        return base
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _prepare_working_repo(source_repo: Path, in_place: bool) -> Path:
    if in_place:
        return source_repo

    working_root = Path(tempfile.mkdtemp(prefix="scheduler-stress-"))
    working_repo = working_root / source_repo.name
    shutil.copytree(source_repo, working_repo)
    return working_repo


def _make_task(repo_path: Path, target_file: Path, prompt: str) -> Task:
    return Task(
        id=uuid.uuid4().hex,
        type="active",
        payload={
            "task": prompt,
            "repo_path": str(repo_path),
            "target_file": str(target_file),
        },
        created_at=time.time(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stress-test the scheduler with three queued mutation tasks against one fixture file.",
    )
    parser.add_argument(
        "--repo-path",
        default=str(DEFAULT_REPO_PATH),
        help="Path to the fixture repository used as the source for the test run.",
    )
    parser.add_argument(
        "--target-file",
        default=str(DEFAULT_TARGET_FILE),
        help="Target file inside the repository to mutate.",
    )
    parser.add_argument(
        "--prompt",
        action="append",
        dest="prompts",
        help="Prompt to queue. Provide exactly three; if omitted, built-in prompts are used.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Mutate the repository directly instead of copying it to a temp working directory.",
    )
    return parser


async def _run(repo_path: Path, target_file: Path, prompts: list[str]) -> None:
    queue = TaskQueue()
    executor = ObservingWorkflowExecutor()
    loop = ExecutionLoop(queue=queue, executor=executor)

    tasks = [_make_task(repo_path, target_file, prompt) for prompt in prompts]
    for task in tasks:
        executor.register(task.id)

    before = target_file.read_text(encoding="utf-8")

    await loop.start()
    try:
        print(f"Repo: {repo_path}")
        print(f"Target: {target_file}")
        print(f"Model: {os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b')}")
        print("--- INPUT PROMPTS ---")
        for index, prompt in enumerate(prompts, start=1):
            print(f"{index}. {prompt}")

        await asyncio.gather(*(queue.enqueue(task) for task in tasks))

        for task in tasks:
            await executor.finished_events[task.id].wait()
            current = target_file.read_text(encoding="utf-8")
            print(f"--- AFTER TASK {task.id[:8]} ---")
            print(current)

        print("--- ORDER ---")
        print(f"start: {executor.start_log}")
        print(f"end:   {executor.end_log}")
        print("--- FINAL CHANGES ---")
        print(f"changed: {before != target_file.read_text(encoding='utf-8')}")
        print(f"errors: {executor.errors}")
        print(f"results: {executor.results}")
    finally:
        await loop.stop()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_repo = _resolve_path(args.repo_path, DEFAULT_REPO_PATH)
    if not source_repo.exists():
        print(f"Repository path does not exist: {source_repo}")
        return 1

    prompts = args.prompts or list(DEFAULT_PROMPTS)
    if len(prompts) != 3:
        print("Provide exactly three prompts with --prompt (or omit it to use the defaults).")
        return 1

    working_repo = _prepare_working_repo(source_repo, args.in_place)
    target_file = _resolve_path(args.target_file, working_repo)
    if not target_file.exists():
        print(f"Target file does not exist: {target_file}")
        return 1

    asyncio.run(_run(working_repo, target_file, prompts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())