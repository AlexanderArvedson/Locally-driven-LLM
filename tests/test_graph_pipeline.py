import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.core.ollama_client import LLMResult
from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs
from src.graph.nodes import node_index as nodes_module
from src.graph.workflow import make_graph
from src.observability.context import RunContext


_REPO_ROOT = Path(__file__).resolve().parents[1]


async def _noop_branch_creator(state, run_context):
    """Stub that skips real git operations in pipeline tests."""
    return {"branch_name": "test/add-type-hints"}


async def _noop_graph_resolver(state, run_context):
    """Stub that skips knowledge-graph resolution in pipeline tests."""
    return {"graph_path": None, "repo_sha": "deadbeef"}


async def _noop_retrieval(state, run_context):
    """Stub that returns empty retrieval context in pipeline tests."""
    return {"repository_context": None, "related_file_contents": {}}


async def _noop_git_committer(state, run_context):
    """Stub that skips real git commit in pipeline tests."""
    return {"repo_sha": "deadbeef"}


class TestGraphPipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        ensure_runtime_dirs()
        for log_path in RUNS_DIR.glob("*.jsonl"):
            log_path.unlink()

    async def test_mocked_graph_pipeline_completes_and_logs(self):
        fake_code_result = LLMResult(
            message="def add(a, b):\n    return a + b\n",
            input_tokens=10,
            output_tokens=20,
        )
        fake_semantic_result = LLMResult(
            message='{"passed": true, "task_alignment_score": 0.9, "regression_risk": 0.1, "missing_requirements": [], "incorrect_behaviors": [], "unnecessary_changes": [], "notes": "change looks correct", "confidence": 0.9}',
            input_tokens=10,
            output_tokens=50,
        )

        async def _fake_chat(messages, **kwargs):
            # Semantic validator prompts are identified by the [DIFF] section.
            user_prompt = messages[1]["content"] if len(messages) > 1 else ""
            if "[DIFF]" in user_prompt:
                return fake_semantic_result
            return fake_code_result

        # Keep a reference to fake_result for the generated_code assertion below.
        fake_result = fake_code_result

        with tempfile.TemporaryDirectory() as tmp_dir:
            target_file = Path(tmp_dir) / "example.py"
            shutil.copyfile(_REPO_ROOT / "sandbox" / "example.py", target_file)

            run_context = RunContext.new()
            graph = make_graph(run_context)

            with (
                patch.object(nodes_module, "branch_creator_node", new=_noop_branch_creator),
                patch.object(nodes_module, "graph_resolver_node", new=_noop_graph_resolver),
                patch.object(nodes_module, "retrieval_node", new=_noop_retrieval),
                patch.object(nodes_module, "git_committer_node", new=_noop_git_committer),
                patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=_fake_chat)) as mock_chat,
            ):
                # Recompile graph inside the patch context so node stubs are picked up.
                graph = make_graph(run_context)
                result = await graph.ainvoke(
                    {
                        "task": "Add type hints to the function.",
                        "target_file": str(target_file),
                    }
                )

            self.assertGreaterEqual(mock_chat.await_count, 1)

            self.assertEqual(result["generated_code"], fake_result.message)
            self.assertGreaterEqual(result["iteration"], 1)
            self.assertTrue(result["review_passed"])
            self.assertIn("updated_code", result)
            self.assertIn("def add(a, b):", target_file.read_text(encoding="utf-8"))

            log_path = RUNS_DIR / f"{run_context.run_id}.jsonl"
            self.assertTrue(log_path.exists(), "Expected runtime JSONL log was not created")

            events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            event_nodes = [event["node"] for event in events]
            for expected_node in (
                "file_reader_node",
                "coder_node",
                "diff_generator_node",
                "static_validator_node",
                "verifier_node",
                "semantic_validator_node",
                "file_writer_node",
            ):
                self.assertIn(expected_node, event_nodes)

            self.assertGreaterEqual(len(events), 6)
            self.assertTrue(all(event["status"] == "success" for event in events))
            self.assertTrue(all("timestamp" in event for event in events))
