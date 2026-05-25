import asyncio
from pathlib import Path

from src.graph.workflow import make_graph
from src.observability.context import RunContext


async def main():
    target_file = Path("sandbox/example.py")
    before = target_file.read_text(encoding="utf-8")

    run_context = RunContext.new()
    graph = make_graph(run_context)

    result = await graph.ainvoke({
        "task": "Add type hints to the function.",
        "target_file": str(target_file),
    })

    after = target_file.read_text(encoding="utf-8")

    print("=== BEFORE ===")
    print(before)
    print("=== AFTER ===")
    print(after)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())