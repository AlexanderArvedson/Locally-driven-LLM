import asyncio

from src.graph.workflow import graph


async def main():
    result = await graph.ainvoke({
        "task": "Write a Python fibonacci function"
    })

    print("\n=== FINAL STATE ===\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())