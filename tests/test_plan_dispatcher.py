"""Tests for plan_dispatcher_node."""

import tempfile
import unittest
from pathlib import Path

from src.graph.state import GraphState
from src.observability.context import RunContext


def _make_plan(*files: str) -> list[dict]:
    return [
        {"file": f, "operation": "modify", "symbol": "sym", "change": "do it", "reason": "reason"}
        for f in files
    ]


class TestPlanDispatcherNode(unittest.IsolatedAsyncioTestCase):
    async def test_dispatches_first_step(self):
        with tempfile.TemporaryDirectory() as td:
            a = str(Path(td) / "a.py")
            b = str(Path(td) / "b.py")
            plan = _make_plan(a, b)
            state: GraphState = {"change_plan": plan, "current_plan_step": 0}

            from src.graph.nodes.plan_dispatcher import plan_dispatcher_node
            result = await plan_dispatcher_node(state, RunContext.new())

        assert result["target_file"] == a
        assert result["current_plan_step"] == 1
        assert result["is_intermediate_step"] is True
        assert result["active_plan_step"]["file"] == a

    async def test_dispatches_last_step_as_non_intermediate(self):
        with tempfile.TemporaryDirectory() as td:
            a = str(Path(td) / "a.py")
            b = str(Path(td) / "b.py")
            plan = _make_plan(a, b)
            state: GraphState = {"change_plan": plan, "current_plan_step": 1}

            from src.graph.nodes.plan_dispatcher import plan_dispatcher_node
            result = await plan_dispatcher_node(state, RunContext.new())

        assert result["target_file"] == b
        assert result["current_plan_step"] == 2
        assert result["is_intermediate_step"] is False

    async def test_resets_per_file_state(self):
        with tempfile.TemporaryDirectory() as td:
            a = str(Path(td) / "a.py")
            plan = _make_plan(a)
            state: GraphState = {
                "change_plan": plan,
                "current_plan_step": 0,
                "iteration": 5,
                "review_passed": True,
                "verification_passed": True,
                "generated_code": "old code",
                "review_errors": ["error1"],
            }

            from src.graph.nodes.plan_dispatcher import plan_dispatcher_node
            result = await plan_dispatcher_node(state, RunContext.new())

        assert result["iteration"] == 0
        assert result["review_passed"] is None
        assert result["verification_passed"] is None
        assert result["generated_code"] is None
        assert result["review_errors"] is None

    async def test_refreshes_related_file_contents_for_modified_files(self):
        with tempfile.TemporaryDirectory() as td:
            prev = str(Path(td) / "prev.py")
            target = str(Path(td) / "target.py")
            Path(prev).write_text("updated content", encoding="utf-8")

            plan = _make_plan(target)
            state: GraphState = {
                "change_plan": plan,
                "current_plan_step": 0,
                "modified_files": [prev],
                "related_file_contents": {prev: "old content"},
            }

            from src.graph.nodes.plan_dispatcher import plan_dispatcher_node
            result = await plan_dispatcher_node(state, RunContext.new())

        # related_file_contents for prev should be refreshed from disk
        assert result["related_file_contents"][prev] == "updated content"

    async def test_raises_on_out_of_range_step(self):
        plan = _make_plan("/tmp/a.py")
        state: GraphState = {"change_plan": plan, "current_plan_step": 5}

        from src.graph.nodes.plan_dispatcher import plan_dispatcher_node
        with self.assertRaises(IndexError):
            await plan_dispatcher_node(state, RunContext.new())

    async def test_raises_when_change_plan_missing(self):
        state: GraphState = {}
        from src.graph.nodes.plan_dispatcher import plan_dispatcher_node
        with self.assertRaises(Exception):
            await plan_dispatcher_node(state, RunContext.new())
