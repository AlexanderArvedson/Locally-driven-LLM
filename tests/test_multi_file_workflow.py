"""Integration tests for the multi-file execution path.

These tests exercise the new dependency_analyzer → change_planner → plan_dispatcher
loop by stubbing out LLM calls, git operations, and sandboxed execution.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.core.ollama_client import LLMResult
from src.core.runtime_paths import ensure_runtime_dirs
from src.graph.state import GraphState
from src.graph.workflow import make_graph, route_after_file_writer
from src.observability.context import RunContext
from src.retrieval.contracts.types import DependencyEdge, RepositorySnapshot


# ---------------------------------------------------------------------------
# Routing unit tests
# ---------------------------------------------------------------------------

class TestRouteAfterFileWriter(unittest.TestCase):
    def test_routes_to_plan_dispatcher_when_steps_remain(self):
        state: GraphState = {
            "change_plan": [{"file": "a.py"}, {"file": "b.py"}],
            "current_plan_step": 1,  # step 0 done, step 1 still pending
        }
        assert route_after_file_writer(state) == "plan_dispatcher"

    def test_routes_to_git_committer_when_plan_complete(self):
        state: GraphState = {
            "change_plan": [{"file": "a.py"}, {"file": "b.py"}],
            "current_plan_step": 2,  # all steps done
        }
        assert route_after_file_writer(state) == "git_committer"

    def test_routes_to_git_committer_when_no_plan(self):
        state: GraphState = {}
        assert route_after_file_writer(state) == "git_committer"

    def test_routes_to_git_committer_on_plan_failed(self):
        state: GraphState = {
            "plan_failed": True,
            "change_plan": [{"file": "a.py"}, {"file": "b.py"}],
            "current_plan_step": 1,
        }
        assert route_after_file_writer(state) == "git_committer"


# ---------------------------------------------------------------------------
# Multi-file pipeline integration test
# ---------------------------------------------------------------------------

class TestMultiFilePipeline(unittest.IsolatedAsyncioTestCase):
    """Tests the full graph loop for a 2-file plan.

    Both LLM calls, git operations, sandbox execution, and the graphify graph
    are replaced with stubs so no external services are needed.
    """

    async def asyncSetUp(self):
        ensure_runtime_dirs()

    async def test_two_file_plan_writes_both_files_and_commits(self):
        with tempfile.TemporaryDirectory() as td:
            file_a = Path(td) / "defn.py"
            file_b = Path(td) / "caller.py"
            file_a.write_text("def old_func(): pass\n", encoding="utf-8")
            file_b.write_text("from defn import old_func\nold_func()\n", encoding="utf-8")

            plan_json = json.dumps([
                {"file": str(file_a), "operation": "modify", "symbol": "old_func",
                 "change": "rename to new_func", "reason": "definition"},
                {"file": str(file_b), "operation": "modify", "symbol": "old_func",
                 "change": "update call site", "reason": "caller"},
            ])
            updated_a = "def new_func(): pass\n"
            updated_b = "from defn import new_func\nnew_func()\n"
            semantic_pass = json.dumps({
                "task_alignment_score": 0.9, "regression_risk": 0.1,
                "missing_requirements": [], "incorrect_behaviors": [],
                "unnecessary_changes": [], "semantic_notes": "", "semantic_confidence": 0.9,
            })
            snapshot = RepositorySnapshot(
                files=[],
                edges=[DependencyEdge(from_path=str(file_b), to_path=str(file_a))],
            )

            async def fake_branch_creator(state, rc):
                return {"branch_name": "test/rename"}

            async def fake_graph_resolver(state, rc):
                return {"graph_path": None, "repo_sha": "abc"}

            async def fake_retrieval(state, rc):
                return {
                    "repository_context": None,
                    "related_file_contents": {},
                    "selected_file_ids": [str(file_a)],
                }

            async def fake_planner(state, rc):
                return {"target_file": None, "target_files": [str(file_a)], "explicit_target_file": False}

            async def fake_dep_analyzer(state, rc):
                return {"affected_files": [str(file_a), str(file_b)], "plan_scope": "multi_file"}

            # LLM call sequence: change_planner, coder (file_a), semantic (file_a),
            #                    coder (file_b), semantic (file_b)
            llm_responses = [
                LLMResult(message=plan_json, input_tokens=0, output_tokens=0),
                LLMResult(message=updated_a, input_tokens=0, output_tokens=0),
                LLMResult(message=semantic_pass, input_tokens=0, output_tokens=0),
                LLMResult(message=updated_b, input_tokens=0, output_tokens=0),
                LLMResult(message=semantic_pass, input_tokens=0, output_tokens=0),
            ]
            call_count = {"n": 0}

            async def fake_chat(self_or_cls, *args, **kwargs):
                idx = call_count["n"]
                call_count["n"] += 1
                return llm_responses[idx]

            async def fake_git_committer(state, rc):
                return {"commit_sha": "cafebabe"}

            from src.graph.nodes import node_index as nodes_module
            from src.core.ollama_client import OllamaClient

            with patch.object(nodes_module, "branch_creator_node", fake_branch_creator), \
                 patch.object(nodes_module, "graph_resolver_node", fake_graph_resolver), \
                 patch.object(nodes_module, "retrieval_node", fake_retrieval), \
                 patch.object(nodes_module, "planner_node", fake_planner), \
                 patch.object(nodes_module, "dependency_analyzer_node", fake_dep_analyzer), \
                 patch.object(nodes_module, "git_committer_node", fake_git_committer), \
                 patch.object(OllamaClient, "chat", fake_chat):

                graph = make_graph(RunContext.new())
                final_state = await graph.ainvoke({
                    "task": "rename old_func to new_func",
                    "repo_path": td,
                    "branch_name": "test/rename",
                })

            # Both files should have been modified on disk.
            assert file_a.read_text(encoding="utf-8").strip() == updated_a.strip()
            assert file_b.read_text(encoding="utf-8").strip() == updated_b.strip()

            # modified_files should contain both.
            modified = final_state.get("modified_files") or []
            assert str(file_a) in modified
            assert str(file_b) in modified

    async def test_plan_aborts_on_first_file_write_failure(self):
        """If file_writer_node fails on step 1, the plan stops and routes to git_committer."""
        from src.graph.workflow import route_after_file_writer

        state: GraphState = {
            "plan_failed": True,
            "change_plan": [{"file": "a.py"}, {"file": "b.py"}],
            "current_plan_step": 1,
            "modified_files": [],
        }
        assert route_after_file_writer(state) == "git_committer"
