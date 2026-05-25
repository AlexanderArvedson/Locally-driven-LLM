from src.core.ollama_client import OllamaClient
from src.graph.state import GraphState
from src.tools.files import read_file, write_file
from src.tools.patches import generate_ndiff, apply_ndiff


client = OllamaClient(base_url="http://localhost:11434")
MAX_ITERATIONS = 3


def _require_state_value(state: GraphState, key: str) -> str:
    value = state.get(key)
    if value is None:
        raise ValueError(f"Missing required state value: {key}")

    return value


def _strip_code_fences(content: str) -> str:
    lines = content.strip().splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip("\n")


def _validate_python_syntax(content: str) -> tuple[bool, str]:
    if not content.strip():
        return False, "Generated code is empty."

    try:
        compile(content, "<generated_code>", "exec")
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno is not None else "an unknown line"
        return False, f"Generated code has a syntax error at {location}: {exc.msg}"

    return True, ""


# Takes the target file path from the state, reads its content, and returns it in a dictionary. 
# This node is responsible for loading the original code that will be modified by the coder node.
async def file_reader_node(state: GraphState) -> dict:
    target_file = _require_state_value(state, "target_file")
    return {
        "original_code": read_file(target_file),
    }


# Takes the generated code from the state and writes it back to the target file.
# This node is responsible for saving the modifications made by the coder node to the filesystem.
async def file_writer_node(state: GraphState) -> dict:
    target_file = _require_state_value(state, "target_file")
    generated_code = _strip_code_fences(_require_state_value(state, "generated_code"))
    # If a diff was provided, apply it; otherwise write the full file.
    if state.get("generated_diff"):
        apply_ndiff(target_file, _require_state_value(state, "generated_diff"))
    else:
        write_file(target_file, generated_code)

    return {
        "updated_code": generated_code,
    }


# This node generate code based on the task, original code, and any review feedback. 
# It constructs a prompt for the LLM and calls the Ollama client to get the modified code.
async def coder_node(state: GraphState) -> dict:
    iteration = state.get("iteration", 0) + 1
    review_feedback = state.get("review_feedback")
    original_code = _require_state_value(state, "original_code")

    user_prompt = (
        f"Task: {state['task']}\n\n"
        f"Target file: {state.get('target_file', '')}\n\n"
        f"File content:\n{original_code}\n\n"
        "Return the FULL updated file only as plain text.\n"
        "Do NOT wrap your output in markdown code fences (```), backticks, or add any explanation.\n"
        "Output should be the literal file contents to write to disk."
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
    code = _strip_code_fences(_require_state_value(state, "generated_code"))
    passed, feedback = _validate_python_syntax(code)

    return {
        "review_passed": passed,
        "review_feedback": feedback,
    }


# This node performs a final verification step by executing the generated code in an isolated namespace to catch any runtime errors.
async def verifier_node(state: GraphState) -> dict:
    code = _strip_code_fences(_require_state_value(state, "generated_code"))

    # First, ensure syntax is valid (should already be true after reviewer)
    passed, feedback = _validate_python_syntax(code)
    if not passed:
        return {"verification_passed": False, "verification_feedback": feedback}

    # Run the code in an isolated namespace to catch runtime errors on import/definition
    ns: dict = {}
    try:
        exec(code, ns)
    except Exception as exc:
        return {"verification_passed": False, "verification_feedback": f"Runtime exec error: {exc}"}

    # Optional smoke test: if a function named `add` exists, call it once.
    if "add" in ns and callable(ns["add"]):
        try:
            ns["add"](1, 2)
        except Exception as exc:
            return {"verification_passed": False, "verification_feedback": f"Runtime test failed: {exc}"}

    return {"verification_passed": True, "verification_feedback": ""}

# This node generates a diff between the original code and the generated code using the ndiff format.
async def diff_generator_node(state: GraphState) -> dict:
    original = _require_state_value(state, "original_code")
    generated = _strip_code_fences(_require_state_value(state, "generated_code"))
    nd = generate_ndiff(original, generated)
    return {"generated_diff": nd}