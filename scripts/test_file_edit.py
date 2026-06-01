import asyncio
from pathlib import Path

from src.graph.workflow import make_graph
from src.observability.context import RunContext
from src.scheduler.state_factory import GraphStateFactory
from src.scheduler.task_request import TaskRequest


_REPO_ROOT = Path(__file__).resolve().parents[1]


async def main():
    target_file = _REPO_ROOT / "sandbox" / "example.py"
    before = target_file.read_text(encoding="utf-8")

    run_context = RunContext.new()
    graph = make_graph(run_context)

    request = TaskRequest(
        task="Add type hints to the function.",
        repo_path=str(_REPO_ROOT),
        target_path=str(target_file),
    )
    result = await graph.ainvoke(GraphStateFactory.from_task_request(request))

    after = target_file.read_text(encoding="utf-8")

    print("=== BEFORE ===")
    print(before)
    print("=== AFTER ===")
    print(after)
    print("=== GRAPH OUTPUT ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
