"""Tests for change_planner_node."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.graph.state import GraphState
from src.observability.context import RunContext


def _make_state(task: str, affected_files: list[str]) -> GraphState:
    return {
        "task": task,
        "affected_files": affected_files,
        "repo_path": "/tmp/repo",
        "repository_context": None,
    }


class TestParsePlan(unittest.TestCase):
    def test_valid_json_array_parsed(self):
        from src.graph.nodes.change_planner import _parse_plan

        valid_files = ["/repo/a.py", "/repo/b.py"]
        raw = json.dumps([
            {"file": "/repo/a.py", "operation": "modify", "symbol": "foo", "change": "rename to bar", "reason": "definition"},
            {"file": "/repo/b.py", "operation": "modify", "symbol": "foo", "change": "update call site", "reason": "caller"},
        ])
        result = _parse_plan(raw, valid_files)
        assert len(result) == 2
        assert result[0]["file"] == "/repo/a.py"
        assert result[0]["symbol"] == "foo"
        assert result[1]["file"] == "/repo/b.py"

    def test_unknown_file_paths_filtered(self):
        from src.graph.nodes.change_planner import _parse_plan

        valid_files = ["/repo/a.py"]
        raw = json.dumps([
            {"file": "/repo/a.py", "operation": "modify", "symbol": "x", "change": "y", "reason": "z"},
            {"file": "/repo/hallucinated.py", "operation": "modify", "symbol": "x", "change": "y", "reason": "z"},
        ])
        result = _parse_plan(raw, valid_files)
        assert len(result) == 1
        assert result[0]["file"] == "/repo/a.py"

    def test_json_inside_markdown_fences_parsed(self):
        from src.graph.nodes.change_planner import _parse_plan

        valid_files = ["/repo/a.py"]
        raw = "```json\n" + json.dumps([
            {"file": "/repo/a.py", "operation": "modify", "symbol": "x", "change": "y", "reason": "z"}
        ]) + "\n```"
        result = _parse_plan(raw, valid_files)
        assert len(result) == 1

    def test_empty_response_returns_empty_list(self):
        from src.graph.nodes.change_planner import _parse_plan

        result = _parse_plan("not json at all", ["/repo/a.py"])
        assert result == []

    def test_missing_fields_get_empty_string_defaults(self):
        from src.graph.nodes.change_planner import _parse_plan

        valid_files = ["/repo/a.py"]
        raw = json.dumps([{"file": "/repo/a.py"}])
        result = _parse_plan(raw, valid_files)
        assert result[0]["symbol"] == ""
        assert result[0]["change"] == ""
        assert result[0]["reason"] == ""
        assert result[0]["operation"] == "modify"


class TestTopologicalOrder(unittest.TestCase):
    def test_definitions_before_callers(self):
        """The file with fewer importers (the definition) should come first."""
        import tempfile
        from pathlib import Path
        from src.retrieval.contracts.types import DependencyEdge, RepositorySnapshot

        with tempfile.TemporaryDirectory() as td:
            defn = str(Path(td) / "defn.py")
            caller = str(Path(td) / "caller.py")
            Path(defn).touch()
            Path(caller).touch()

            # caller imports from defn; defn has 0 importers, caller has 1
            snapshot = RepositorySnapshot(
                files=[],
                edges=[DependencyEdge(from_path=caller, to_path=defn)],
            )
            with patch("src.graph.nodes.change_planner.AstIndexer") as mock_cls:
                mock_cls.return_value.build_snapshot.return_value = snapshot
                from src.graph.nodes.change_planner import _topological_order
                result = _topological_order([caller, defn], td)

        assert result[0] == defn
        assert result[1] == caller

    def test_fallback_to_original_order_on_error(self):
        from src.graph.nodes.change_planner import _topological_order

        with patch("src.graph.nodes.change_planner.AstIndexer", side_effect=RuntimeError("boom")):
            result = _topological_order(["a.py", "b.py"], "/tmp")

        assert result == ["a.py", "b.py"]


class TestChangePlannerNode(unittest.IsolatedAsyncioTestCase):
    async def test_returns_change_plan_on_valid_llm_output(self):
        files = ["/repo/a.py", "/repo/b.py"]
        state = _make_state("rename function foo to bar", files)

        plan_json = json.dumps([
            {"file": "/repo/a.py", "operation": "modify", "symbol": "foo", "change": "rename to bar", "reason": "definition"},
            {"file": "/repo/b.py", "operation": "modify", "symbol": "foo", "change": "update call", "reason": "caller"},
        ])

        from src.core.ollama_client import LLMResult

        with patch("src.graph.nodes.change_planner.client") as mock_client, \
             patch("src.graph.nodes.change_planner.AstIndexer") as mock_indexer_cls:
            from src.retrieval.contracts.types import RepositorySnapshot
            mock_indexer_cls.return_value.build_snapshot.return_value = RepositorySnapshot(files=[], edges=[])
            mock_client.chat = AsyncMock(return_value=LLMResult(message=plan_json, input_tokens=0, output_tokens=0))

            from src.graph.nodes.change_planner import change_planner_node
            result = await change_planner_node(state, RunContext.new())

        assert "change_plan" in result
        assert len(result["change_plan"]) == 2
        assert result["change_plan"][0]["symbol"] == "foo"

    async def test_returns_planner_error_on_empty_plan(self):
        state = _make_state("task", ["/repo/a.py"])

        from src.core.ollama_client import LLMResult

        with patch("src.graph.nodes.change_planner.client") as mock_client, \
             patch("src.graph.nodes.change_planner.AstIndexer") as mock_indexer_cls:
            from src.retrieval.contracts.types import RepositorySnapshot
            mock_indexer_cls.return_value.build_snapshot.return_value = RepositorySnapshot(files=[], edges=[])
            mock_client.chat = AsyncMock(return_value=LLMResult(message="[]", input_tokens=0, output_tokens=0))

            from src.graph.nodes.change_planner import change_planner_node
            result = await change_planner_node(state, RunContext.new())

        assert "planner_error" in result

    async def test_raises_when_affected_files_missing(self):
        state = {"task": "rename", "repo_path": "/tmp"}

        from src.graph.nodes.change_planner import change_planner_node
        with self.assertRaises(Exception):
            await change_planner_node(state, RunContext.new())
