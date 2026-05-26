import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.core.ollama_client import LLMResult
from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs
from src.graph.nodes import nodes as nodes_module
from src.graph.workflow import make_graph
from src.observability.context import RunContext


class TestGraphPipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        ensure_runtime_dirs()
        for log_path in RUNS_DIR.glob("*.jsonl"):
            log_path.unlink()

    async def test_mocked_graph_pipeline_completes_and_logs(self):
        fake_result = LLMResult(
            message="def add(a, b):\n    return a + b\n",
            input_tokens=10,
            output_tokens=20,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            target_file = Path(tmp_dir) / "example.py"
            shutil.copyfile(Path("sandbox/example.py"), target_file)

            run_context = RunContext.new()
            graph = make_graph(run_context)

            with patch.object(nodes_module.client, "chat", new=AsyncMock(return_value=fake_result)) as mock_chat:
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
                "reviewer_node",
                "verifier_node",
                "file_writer_node",
            ):
                self.assertIn(expected_node, event_nodes)

            self.assertGreaterEqual(len(events), 6)
            self.assertTrue(all(event["run_id"] == run_context.run_id for event in events))
            self.assertTrue(all(event["status"] == "success" for event in events))
            self.assertTrue(all("timestamp" in event for event in events))
