import asyncio
import importlib
import types
import unittest
from unittest.mock import AsyncMock, patch

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.retrieval.contracts.context_contract import build_repository_context_payload
from src.retrieval.contracts.types import ContextPackage, DependencyEdge
from tests.support.httpx_stub import httpx_stub


# Use `httpx_stub` to ensure import-time httpx usage doesn't break tests.


class TestCoderPromptContract(unittest.TestCase):
    def test_missing_repository_context_has_controlled_prompt_marker(self):
        with httpx_stub():
            nodes_module = importlib.import_module("src.graph.nodes.node_index")
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
            nodes_module = importlib.import_module("src.graph.nodes.node_index")
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

        # Verify deterministic structure: must contain all required sections.
        prompt = captured_prompts[0]
        self.assertIn("[TASK]", prompt)
        self.assertIn("[TARGET FILE]", prompt)
        self.assertIn("[FILE CONTENT]", prompt)
        self.assertIn("[REPOSITORY CONTEXT]", prompt)
        self.assertIn("- selected_files:", prompt)
        self.assertIn("[INSTRUCTION]", prompt)
        self.assertIn("Only modify the target file.", prompt)


if __name__ == "__main__":
    unittest.main()
