import asyncio
import importlib
import sys
import types
import unittest
from typing import Any, cast
from unittest.mock import AsyncMock, patch

from src.observability.context import RunContext


def _load_nodes_module_with_optional_httpx_stub():
    """Import `src.graph.nodes.nodes` even when `httpx` is unavailable."""
    original_httpx = sys.modules.get("httpx")
    inserted_stub = False
    if original_httpx is None:
        dummy = types.ModuleType("httpx")

        class _DummyAsyncClient:
            def __init__(self, timeout=None):
                pass

            async def post(self, *args, **kwargs):
                class _Resp:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {"message": {"content": ""}}

                return _Resp()

            async def aclose(self):
                return None

        httpx_mod: Any = dummy
        httpx_mod.AsyncClient = _DummyAsyncClient
        httpx_mod.HTTPError = Exception
        httpx_mod.HTTPStatusError = type("HTTPStatusError", (), {})
        sys.modules["httpx"] = dummy
        inserted_stub = True

    try:
        return importlib.import_module("src.graph.nodes.nodes"), inserted_stub
    except Exception:
        if inserted_stub:
            sys.modules.pop("httpx", None)
        raise


class TestCoderPromptContract(unittest.TestCase):
    def test_missing_repository_context_has_controlled_prompt_marker(self):
        nodes_module, inserted_stub = _load_nodes_module_with_optional_httpx_stub()
        captured_prompts = []

        async def fake_chat(messages, model, temperature):
            captured_prompts.append(messages[1]["content"])
            return types.SimpleNamespace(message="def x():\n    return 1\n", input_tokens=1, output_tokens=1)

        state = {
            "task": "refactor code",
            "target_file": "a.py",
            "original_code": "def x():\n    return 1\n",
        }

        try:
            with patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=fake_chat)):
                result = asyncio.run(nodes_module.coder_node(state, RunContext.new()))
        finally:
            if inserted_stub:
                sys.modules.pop("httpx", None)

        self.assertIn("generated_code", result)
        self.assertEqual(len(captured_prompts), 1)

        prompt = captured_prompts[0]
        self.assertIn("[REPOSITORY CONTEXT]", prompt)
        self.assertIn("- none", prompt)
        # Guard against silently pretending context entries exist.
        self.assertNotIn("- selected_files:", prompt)

    def test_prompt_snapshot_and_ordering_is_deterministic(self):
        nodes_module, inserted_stub = _load_nodes_module_with_optional_httpx_stub()
        captured_prompts = []

        async def fake_chat(messages, model, temperature):
            captured_prompts.append(messages[1]["content"])
            return types.SimpleNamespace(message="def x():\n    return 1\n", input_tokens=1, output_tokens=1)

        state = {
            "task": "refactor code",
            "target_file": "a.py",
            "original_code": "def x():\n    return 1\n",
            "repository_context": {
                "primary_file": "a.py",
                "selected_files": ["a.py", "b.py", "test_a.py"],
                # Intentionally unsorted to verify formatter normalization.
                "related_symbols": {
                    "test_a.py": ["test_case"],
                    "a.py": ["x"],
                    "b.py": ["helper"],
                },
                "dependency_summary": [
                    {"from_path": "a.py", "to_path": "b", "import_text": "b"},
                ],
                "total_symbols": 3,
            },
        }

        try:
            with patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=fake_chat)):
                asyncio.run(nodes_module.coder_node(state, RunContext.new()))
                asyncio.run(nodes_module.coder_node(state, RunContext.new()))
        finally:
            if inserted_stub:
                sys.modules.pop("httpx", None)

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
