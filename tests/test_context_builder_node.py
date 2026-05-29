import asyncio
import os
import tempfile
import unittest

from pathlib import Path

from src.retrieval.assembly.context_assembler import ContextAssembler
from src.retrieval.ranking.heuristic_ranker import HeuristicRanker
from src.retrieval.indexing.ast_indexer import AstIndexer
from tests.support.httpx_stub import httpx_stub

from src.observability.context import RunContext
from src.graph.nodes.retrieval_node import retrieval_node


class TestRetrievalNode(unittest.TestCase):
    def test_retrieval_node_creates_context_payload(self):
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
                    result = await retrieval_node(state, run_context)

                # State must NOT contain heavyweight snapshot or graph handle.
                self.assertNotIn("repository_snapshot", state)
                self.assertNotIn("graph_handle", state)

                # Lightweight retrieval references must be present in the result.
                self.assertIn("retrieval_session_id", result)
                self.assertIn("selected_file_ids", result)
                self.assertIn("graph_snapshot_sha", result)

                # Versioned context payload must be populated.
                self.assertIn("repository_context", result)
                pkg = result["repository_context"]
                self.assertEqual(pkg["primary_file"], os.path.relpath(str(a_path), str(repo_path)))
                self.assertEqual(pkg["selected_files"][0], pkg["primary_file"])
                self.assertIn(os.path.relpath(str(b_path), str(repo_path)), pkg["selected_files"])

            asyncio.run(run_node())


if __name__ == "__main__":
    unittest.main()
