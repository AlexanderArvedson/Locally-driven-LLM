# This script tests the file editing capabilities of the graph workflow. It reads a target file, invokes the graph to modify it, 
# and then prints the before and after contents of the file along with the graph's output.

import asyncio
from pathlib import Path

from src.graph.workflow import graph


async def main():
    target_file = Path("sandbox/example.py")
    before = target_file.read_text(encoding="utf-8")

    result = await graph.ainvoke(
        {
            "task": "Add type hints to the function.",
            "target_file": str(target_file),
        }
    )

    after = target_file.read_text(encoding="utf-8")

    print("=== BEFORE ===")
    print(before)
    print("=== AFTER ===")
    print(after)
    print("=== GRAPH OUTPUT ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
