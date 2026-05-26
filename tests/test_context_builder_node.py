import asyncio
import importlib
import unittest
import sys
import types
from typing import Any, cast
from unittest.mock import patch

from src.observability.context import RunContext
from src.repository.repository_types import RepositorySnapshot, FileNode, Symbol, DependencyEdge, ContextPackage


class TestContextBuilderNode(unittest.TestCase):
    def test_context_builder_node_creates_snapshot_and_context(self):
        # Prepare a small deterministic snapshot
        a = FileNode(path="a.py", language="python", size=10, symbols=[Symbol(name="foo", kind="function")], imports=["b"])
        b = FileNode(path="b.py", language="python", size=20, symbols=[Symbol(name="Bar", kind="class"), Symbol(name="Bar.method", kind="method")], imports=[])
        snapshot = RepositorySnapshot(files=[a, b], edges=[DependencyEdge(from_path="a.py", to_path="b", import_text="b")])


        async def run_node_with_patched_indexer():
            state = {"task": "do something", "target_file": "a.py"}
            run_context = RunContext.new()

            # Import the nodes module while temporarily stubbing httpx if it's missing.
            orig_httpx = sys.modules.get("httpx")
            inserted = False
            if orig_httpx is None:
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

                # Use a typed Any reference so static checkers don't complain
                httpx_mod: Any = dummy
                httpx_mod.AsyncClient = _DummyAsyncClient
                httpx_mod.HTTPError = Exception
                httpx_mod.HTTPStatusError = Exception
                sys.modules["httpx"] = dummy
                inserted = True

            try:
                nodes_mod = importlib.import_module("src.graph.nodes.nodes")
                context_builder = nodes_mod.context_builder_node

                with patch("src.graph.nodes.nodes.SimpleRepositoryIndexer.build_snapshot", return_value=snapshot):
                    result = await context_builder(state, run_context)
            finally:
                if inserted:
                    # restore clean state so other tests can import real httpx
                    sys.modules.pop("httpx", None)

            # State should include repository_context and repository_snapshot (cached)
            self.assertIn("repository_context", state)
            self.assertIn("repository_snapshot", state)
            self.assertIsNotNone(state["repository_context"])

            pkg = cast(ContextPackage, state["repository_context"])
            self.assertEqual(pkg.primary_file, "a.py")
            self.assertIn("a.py", pkg.related_files)
            self.assertEqual(pkg.total_symbols, 3)

            # The node should also return the context in the result mapping
            self.assertIn("repository_context", result)

        asyncio.run(run_node_with_patched_indexer())


if __name__ == "__main__":
    unittest.main()
