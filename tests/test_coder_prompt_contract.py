import asyncio
import importlib
import types
import unittest
from unittest.mock import AsyncMock, patch

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.repository.context_contract import build_repository_context_payload
from src.repository.repository_types import ContextPackage, DependencyEdge
from tests.support.httpx_stub import httpx_stub


# Use `httpx_stub` to ensure import-time httpx usage doesn't break tests.


class TestCoderPromptContract(unittest.TestCase):
    def test_missing_repository_context_has_controlled_prompt_marker(self):
        with httpx_stub():
            nodes_module = importlib.import_module("src.graph.nodes.nodes")
        captured_prompts = []

        async def fake_chat(messages, model, temperature):
            captured_prompts.append(messages[1]["content"])
            return types.SimpleNamespace(message="def x():\n    return 1\n", input_tokens=1, output_tokens=1)

        state: GraphState = {
            "task": "refactor code",
            "target_file": "a.py",
            "original_code": "def x():\n    return 1\n",
        }

        with patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=fake_chat)):
            result = asyncio.run(nodes_module.coder_node(state, RunContext.new()))

        self.assertIn("generated_code", result)
        self.assertEqual(len(captured_prompts), 1)

        prompt = captured_prompts[0]
        self.assertIn("[REPOSITORY CONTEXT]", prompt)
        self.assertIn("- none", prompt)
        # Guard against silently pretending context entries exist.
        self.assertNotIn("- selected_files:", prompt)

    def test_prompt_snapshot_and_ordering_is_deterministic(self):
        with httpx_stub():
            nodes_module = importlib.import_module("src.graph.nodes.nodes")
        captured_prompts = []

        async def fake_chat(messages, model, temperature):
            captured_prompts.append(messages[1]["content"])
            return types.SimpleNamespace(message="def x():\n    return 1\n", input_tokens=1, output_tokens=1)

        state: GraphState = {
            "task": "refactor code",
            "target_file": "a.py",
            "original_code": "def x():\n    return 1\n",
        }

        context_package = ContextPackage(
            primary_file="a.py",
            related_files=["a.py", "b.py", "test_a.py"],
            related_symbols={
                "test_a.py": ["test_case"],
                "a.py": ["x"],
                "b.py": ["helper"],
            },
            dependency_summary=[
                DependencyEdge(from_path="a.py", to_path="b", import_text="b"),
            ],
            total_symbols=3,
        )
        state["repository_context"] = build_repository_context_payload(
            context_package,
            selected_files=["a.py", "b.py", "test_a.py"],
        )

        with patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=fake_chat)):
            asyncio.run(nodes_module.coder_node(state, RunContext.new()))
            asyncio.run(nodes_module.coder_node(state, RunContext.new()))

        self.assertEqual(len(captured_prompts), 2)
        self.assertEqual(captured_prompts[0], captured_prompts[1])

        expected_prompt = (
            "[TASK]\n"
            "refactor code\n\n"
            "[TARGET FILE]\n"
            "a.py\n\n"
            "[FILE CONTENT]\n"
            "def x():\n"
            "    return 1\n\n\n"
            "[REPOSITORY CONTEXT]\n"
            "- context_version: 1\n"
            "- selected_files:\n"
            "  1. a.py\n"
            "  2. b.py\n"
            "  3. test_a.py\n"
            "- related_symbols:\n"
            "  - a.py: x\n"
            "  - b.py: helper\n"
            "  - test_a.py: test_case\n"
            "- total_symbols: 3\n\n"
            "[INSTRUCTION]\n"
            "Only modify the target file.\n"
            "Use repository context for reasoning only.\n"
            "Return the FULL updated file only as plain text.\n"
            "Do NOT wrap your output in markdown code fences (```), backticks, or add any explanation.\n"
            "Output should be the literal file contents to write to disk."
        )
        self.assertEqual(captured_prompts[0], expected_prompt)


if __name__ == "__main__":
    unittest.main()
