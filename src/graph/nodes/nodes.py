from src.graph.state import GraphState
from src.core.ollama_client import OllamaClient


client = OllamaClient(base_url="http://localhost:11434")


async def coder_node(state: GraphState) -> dict:
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
                "content": state["task"],
            },
        ],
        model="qwen2.5-coder:7b",
        temperature=0.2,
    )

    return {
        "generated_code": result.message,
    }