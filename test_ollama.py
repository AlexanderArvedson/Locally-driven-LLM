import asyncio
from src.core.ollama_client import OllamaClient


async def main():
    client = OllamaClient(base_url="http://localhost:11434")

    try:
        result = await client.chat(
            messages=[
                {
                    "role": "user",
                    "content": "Write a Python function that reverses a string",
                }
            ],
            model="qwen2.5-coder:7b",
            temperature=0.7,
        )

        print(f"\n=== RESPONSE ===\n{result.message}\n")
        print(f"Input tokens: {result.input_tokens}")
        print(f"Output tokens: {result.output_tokens}")

    except Exception as e:
        print(f"Ollama call failed: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())