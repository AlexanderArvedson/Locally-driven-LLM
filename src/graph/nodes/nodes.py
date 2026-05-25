from src.core.ollama_client import OllamaClient
from src.graph.state import GraphState
from src.tools.files import read_file, write_file


client = OllamaClient(base_url="http://localhost:11434")
MAX_ITERATIONS = 3


def _strip_code_fences(content: str) -> str:
    lines = content.strip().splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip("\n")


# Takes the target file path from the state, reads its content, and returns it in a dictionary. 
# This node is responsible for loading the original code that will be modified by the coder node.
async def file_reader_node(state: GraphState) -> dict:
    target_file = state["target_file"]
    return {
        "original_code": read_file(target_file),
    }


# Takes the generated code from the state and writes it back to the target file.
# This node is responsible for saving the modifications made by the coder node to the filesystem.
async def file_writer_node(state: GraphState) -> dict:
    target_file = state["target_file"]
    generated_code = _strip_code_fences(state["generated_code"])
    write_file(target_file, generated_code)

    return {
        "updated_code": generated_code,
    }


# This node generate code based on the task, original code, and any review feedback. 
# It constructs a prompt for the LLM and calls the Ollama client to get the modified code.
async def coder_node(state: GraphState) -> dict:
    iteration = state.get("iteration", 0) + 1
    review_feedback = state.get("review_feedback")

    user_prompt = (
        f"Task: {state['task']}\n\n"
        f"Target file: {state.get('target_file', '')}\n\n"
        f"File content:\n{state['original_code']}\n\n"
        "Return the FULL updated file only.\n"
        "Do not include explanations."
    )
    if review_feedback:
        user_prompt = (
            f"{user_prompt}\n\n"
            f"Previous review feedback: {review_feedback}\n"
            "Revise the code to address the feedback while still returning the full updated file only."
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


# This node reviews the generated code using simple heuristics to determine if it meets basic quality standards.
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