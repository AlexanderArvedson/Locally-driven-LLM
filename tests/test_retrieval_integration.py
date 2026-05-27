import asyncio
import json
import unittest
import types
from unittest.mock import AsyncMock, patch

from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs
from src.repository.context_contract import (
    CONTEXT_VERSION,
    REQUIRED_CONTEXT_FIELDS,
    validate_repository_context_payload,
)
from src.repository.simple_repository_indexer import SimpleRepositoryIndexer
from src.observability.context import RunContext
from tests.support.httpx_stub import httpx_stub
from tests.support.fixture_repo import temporary_fixture_repo


class TestRetrievalIntegration(unittest.TestCase):
    def setUp(self):
        ensure_runtime_dirs()
        for log_path in RUNS_DIR.glob("*.jsonl"):
            log_path.unlink()

    def _run_graph_once(self):
        fake_result = types.SimpleNamespace(
            message="def greet(name):\n    return f'hello {name}'\n",
            input_tokens=7,
            output_tokens=11,
        )

        with temporary_fixture_repo() as repo_copy:
            original_b = (repo_copy / "b.py").read_text(encoding="utf-8")

            indexer = SimpleRepositoryIndexer()
            snapshot = indexer.build_snapshot(str(repo_copy))
            self.assertGreaterEqual(len(snapshot.files), 2)

            run_context = RunContext.new()

            with httpx_stub():
                from src.graph.workflow import make_graph
                from src.graph.nodes import nodes as nodes_module

                graph = make_graph(run_context)

                captured_messages = []

                async def fake_chat(messages, model, temperature):
                    captured_messages.append(messages)
                    user_prompt = messages[1]["content"]
                    self.assertIn("[TASK]", user_prompt)
                    self.assertIn("[TARGET FILE]", user_prompt)
                    self.assertIn("[FILE CONTENT]", user_prompt)
                    self.assertIn("[REPOSITORY CONTEXT]", user_prompt)
                    self.assertIn("selected_files", user_prompt)
                    self.assertIn("[INSTRUCTION]", user_prompt)
                    self.assertIn("Only modify the target file.", user_prompt)
                    return fake_result

                with patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=fake_chat)):
                    result = asyncio.run(
                        graph.ainvoke(
                            {
                                "task": "refactor code",
                                "repo_path": str(repo_copy),
                            }
                        )
                    )

            self.assertIn("repository_context", result)
            ctx = result["repository_context"]
            for key in REQUIRED_CONTEXT_FIELDS:
                self.assertIn(key, ctx)
            self.assertEqual(ctx["context_version"], CONTEXT_VERSION)
            is_valid, reason = validate_repository_context_payload(ctx)
            self.assertTrue(is_valid, msg=reason)

            self.assertIn("selected_files", ctx)
            self.assertIsInstance(ctx["selected_files"], list)
            self.assertGreater(len(ctx["selected_files"]), 0)
            self.assertEqual(ctx["selected_files"][0], "a.py")

            dependency_summary = ctx.get("dependency_summary", [])
            rendered_order = [
                (edge.get("from_path", ""), edge.get("to_path", ""))
                for edge in dependency_summary
            ]
            self.assertEqual(rendered_order, sorted(rendered_order))

            self.assertEqual((repo_copy / "b.py").read_text(encoding="utf-8"), original_b)
            self.assertGreaterEqual(len(captured_messages), 1)

            log_path = RUNS_DIR / f"{run_context.run_id}.jsonl"
            self.assertTrue(log_path.exists(), "Expected runtime JSONL log was not created")
            events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            event_nodes = [event["node"] for event in events]
            self.assertIn("context_builder_node", event_nodes)

            return result

    def _run_graph_once_for_fixture(self, fixture_name: str, task: str):
        fake_result = types.SimpleNamespace(
            message="def greet(name):\n    return f'hello {name}'\n",
            input_tokens=7,
            output_tokens=11,
        )

        with temporary_fixture_repo(fixture_name) as repo_copy:
            original_service = (repo_copy / "app" / "services" / "task_service.py").read_text(encoding="utf-8")

            indexer = SimpleRepositoryIndexer()
            snapshot = indexer.build_snapshot(str(repo_copy))
            self.assertGreaterEqual(len(snapshot.files), 3)

            run_context = RunContext.new()

            with httpx_stub():
                from src.graph.workflow import make_graph
                from src.graph.nodes import nodes as nodes_module

                graph = make_graph(run_context)

                captured_messages = []

                async def fake_chat(messages, model, temperature):
                    captured_messages.append(messages)
                    user_prompt = messages[1]["content"]
                    self.assertIn("[TASK]", user_prompt)
                    self.assertIn("[TARGET FILE]", user_prompt)
                    self.assertIn("[FILE CONTENT]", user_prompt)
                    self.assertIn("[REPOSITORY CONTEXT]", user_prompt)
                    self.assertIn("selected_files", user_prompt)
                    self.assertIn("[INSTRUCTION]", user_prompt)
                    self.assertIn("Only modify the target file.", user_prompt)
                    return fake_result

                with patch.object(nodes_module.client, "chat", new=AsyncMock(side_effect=fake_chat)):
                    result = asyncio.run(
                        graph.ainvoke(
                            {
                                "task": task,
                                "repo_path": str(repo_copy),
                            }
                        )
                    )

            self.assertIn("repository_context", result)
            ctx = result["repository_context"]
            for key in REQUIRED_CONTEXT_FIELDS:
                self.assertIn(key, ctx)
            self.assertEqual(ctx["context_version"], CONTEXT_VERSION)
            is_valid, reason = validate_repository_context_payload(ctx)
            self.assertTrue(is_valid, msg=reason)

            self.assertIn("selected_files", ctx)
            self.assertIsInstance(ctx["selected_files"], list)
            self.assertGreater(len(ctx["selected_files"]), 0)
            self.assertEqual(ctx["selected_files"][0], "app/main.py")
            self.assertIn("app/processing/task_runner.py", ctx["selected_files"])
            self.assertIn("app/services/task_service.py", ctx["selected_files"])
            self.assertIn("app/utils/validators.py", ctx["selected_files"])

            dependency_summary = ctx.get("dependency_summary", [])
            rendered_order = [
                (edge.get("from_path", ""), edge.get("to_path", ""))
                for edge in dependency_summary
            ]
            self.assertEqual(rendered_order, sorted(rendered_order))
            self.assertTrue(
                any(
                    from_path == "app/main.py" and "task_runner" in to_path
                    for from_path, to_path in rendered_order
                )
            )
            self.assertTrue(
                any(
                    from_path == "app/processing/task_runner.py" and "task_service" in to_path
                    for from_path, to_path in rendered_order
                )
            )

            self.assertEqual((repo_copy / "app" / "services" / "task_service.py").read_text(encoding="utf-8"), original_service)

            log_path = RUNS_DIR / f"{run_context.run_id}.jsonl"
            self.assertTrue(log_path.exists(), "Expected runtime JSONL log was not created")
            events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            event_nodes = [event["node"] for event in events]
            self.assertIn("context_builder_node", event_nodes)

            self.assertGreaterEqual(len(captured_messages), 1)

            return result

    def test_retrieval_pipeline_is_deterministic(self):
        run1 = self._run_graph_once()
        run2 = self._run_graph_once()

        self.assertEqual(
            run1["repository_context"]["selected_files"],
            run2["repository_context"]["selected_files"],
        )

    def test_sample_repo_v2_pipeline_is_deterministic(self):
        run1 = self._run_graph_once_for_fixture(
            "sample_repo_v2",
            "refactor the task report pipeline and validation helpers",
        )
        run2 = self._run_graph_once_for_fixture(
            "sample_repo_v2",
            "refactor the task report pipeline and validation helpers",
        )

        self.assertEqual(
            run1["repository_context"]["selected_files"],
            run2["repository_context"]["selected_files"],
        )


if __name__ == "__main__":
    unittest.main()
