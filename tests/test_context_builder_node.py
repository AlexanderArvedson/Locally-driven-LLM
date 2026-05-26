import asyncio
import importlib
import unittest
from typing import Any, Dict, cast
from unittest.mock import patch

from src.observability.context import RunContext
from tests.support.httpx_stub import httpx_stub
from src.repository.repository_types import RepositorySnapshot, FileNode, Symbol, DependencyEdge


class TestContextBuilderNode(unittest.TestCase):
    def test_context_builder_node_creates_snapshot_and_context(self):
        # Prepare a small deterministic snapshot
        a = FileNode(path="a.py", language="python", size=10, symbols=[Symbol(name="foo", kind="function")], imports=["b"])
        b = FileNode(path="b.py", language="python", size=20, symbols=[Symbol(name="Bar", kind="class"), Symbol(name="Bar.method", kind="method")], imports=[])
        snapshot = RepositorySnapshot(files=[a, b], edges=[DependencyEdge(from_path="a.py", to_path="b", import_text="b")])


        async def run_node_with_patched_indexer():
            state = {"task": "do something", "target_file": "a.py"}
            run_context = RunContext.new()

            with httpx_stub():
                nodes_mod = importlib.import_module("src.graph.nodes.nodes")
                context_builder = nodes_mod.context_builder_node

                with patch("src.graph.nodes.nodes.SimpleRepositoryIndexer.build_snapshot", return_value=snapshot):
                    result = await context_builder(state, run_context)

            # State should include repository_context and repository_snapshot (cached)
            self.assertIn("repository_context", state)
            self.assertIn("repository_snapshot", state)
            self.assertIsNotNone(state["repository_context"])

            pkg = cast(Dict[str, Any], state["repository_context"])
            self.assertIn("selected_files", pkg)
            self.assertEqual(pkg["primary_file"], "a.py")
            self.assertIn("a.py", pkg["selected_files"])
            self.assertEqual(pkg["total_symbols"], 3)

            # The node should also return the context in the result mapping
            self.assertIn("repository_context", result)

        asyncio.run(run_node_with_patched_indexer())


if __name__ == "__main__":
    unittest.main()
