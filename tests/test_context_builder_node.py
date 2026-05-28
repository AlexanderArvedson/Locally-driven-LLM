import asyncio
import os
import tempfile
import unittest

from pathlib import Path

from src.repository.context_builder import SimpleContextBuilder
from src.repository.retrieval_engine import SimpleRetrievalEngine
from src.repository.simple_repository_indexer import SimpleRepositoryIndexer
from tests.support.httpx_stub import httpx_stub

from src.observability.context import RunContext
from src.graph.nodes.context_builder import context_builder_node


class TestContextBuilderNode(unittest.TestCase):
    def test_context_builder_node_creates_snapshot_and_context(self):
        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td)
            a_path = repo_path / "a.py"
            b_path = repo_path / "b.py"

            a_path.write_text("import b\n\ndef foo():\n    return 1\n", encoding="utf-8")
            b_path.write_text("def helper():\n    return 2\n", encoding="utf-8")

            async def run_node():
                state = {"task": "do something", "target_file": str(a_path), "repo_path": str(repo_path)}
                run_context = RunContext.new()

                with httpx_stub():
                    result = await context_builder_node(state, run_context)

                self.assertIn("repository_context", state)
                self.assertIn("repository_snapshot", state)
                self.assertEqual(len(state["repository_snapshot"].files), 2)

                pkg = state["repository_context"]
                self.assertEqual(pkg["primary_file"], os.path.relpath(str(a_path), str(repo_path)))
                self.assertEqual(pkg["selected_files"][0], pkg["primary_file"])
                self.assertIn(os.path.relpath(str(b_path), str(repo_path)), pkg["selected_files"])
                self.assertIn("repository_context", result)
                self.assertEqual(result["repository_context"], pkg)

            asyncio.run(run_node())


if __name__ == "__main__":
    unittest.main()
