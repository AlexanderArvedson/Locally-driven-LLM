from src.graph.state import GraphState
from src.core.ollama_client import OllamaClient


client = OllamaClient(base_url="http://localhost:11434")
MAX_ITERATIONS = 3


async def coder_node(state: GraphState) -> dict:
    iteration = state.get("iteration", 0) + 1
    review_feedback = state.get("review_feedback")

    user_prompt = state["task"]
    if review_feedback:
        user_prompt = (
            f"{state['task']}\n\n"
            f"Previous review feedback: {review_feedback}\n"
            "Revise the code to address the feedback."
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

    return {
        "generated_code": result.message,
        "iteration": iteration,
        "review_passed": False,
    }

async def reviewer_node(state: GraphState) -> dict:
    code = state.get("generated_code", "")

    # simple heuristic (temporary)
    passed = (
        "def " in code
        and "TODO" not in code
        and len(code) > 20
    )

    return {
        "review_passed": passed,
        "review_feedback": "Code must include a function definition, avoid TODO markers, and be longer than 20 characters." if not passed else "",
    }