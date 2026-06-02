"""Tests for dependency_analyzer_node."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.graph.state import GraphState
from src.observability.context import RunContext
from src.retrieval.contracts.types import DependencyEdge, RepositorySnapshot


def _make_snapshot(edges: list[tuple[str, str]]) -> RepositorySnapshot:
    dep_edges = [DependencyEdge(from_path=f, to_path=t) for f, t in edges]
    return RepositorySnapshot(files=[], edges=dep_edges)


class TestBuildImporterIndex(unittest.TestCase):
    def test_builds_correct_reverse_index(self):
        from src.graph.nodes.dependency_analyzer import _build_importer_index

        with tempfile.TemporaryDirectory() as td:
            a = str(Path(td) / "a.py")
            b = str(Path(td) / "b.py")
            c = str(Path(td) / "c.py")
            Path(a).touch()
            Path(b).touch()
            Path(c).touch()

            snapshot = _make_snapshot([(b, a), (c, a)])
            with patch("src.graph.nodes.dependency_analyzer.AstIndexer") as mock_cls:
                mock_cls.return_value.build_snapshot.return_value = snapshot
                result = _build_importer_index(td)

        # b imports a, c imports a → importers_of[a] = [b, c]
        assert a in result
        assert set(result[a]) == {b, c}
        # a imports nobody in this snapshot
        assert b not in result
        assert c not in result


class TestExpandWithImporters(unittest.TestCase):
    def test_direct_importers_included(self):
        from src.graph.nodes.dependency_analyzer import _expand_with_importers

        importers = {"file_a": ["file_b", "file_c"]}
        result = _expand_with_importers(["file_a"], importers, depth=1)
        assert "file_a" in result
        assert "file_b" in result
        assert "file_c" in result

    def test_transitive_importers_at_depth_2(self):
        from src.graph.nodes.dependency_analyzer import _expand_with_importers

        importers = {"file_a": ["file_b"], "file_b": ["file_c"]}
        result = _expand_with_importers(["file_a"], importers, depth=2)
        assert "file_c" in result

    def test_no_expansion_at_depth_0(self):
        from src.graph.nodes.dependency_analyzer import _expand_with_importers

        importers = {"file_a": ["file_b"]}
        result = _expand_with_importers(["file_a"], importers, depth=0)
        assert result == ["file_a"]

    def test_deduplicates_across_seeds(self):
        from src.graph.nodes.dependency_analyzer import _expand_with_importers

        importers = {"file_a": ["file_c"], "file_b": ["file_c"]}
        result = _expand_with_importers(["file_a", "file_b"], importers, depth=1)
        assert result.count("file_c") == 1


class TestDependencyAnalyzerNode(unittest.IsolatedAsyncioTestCase):
    async def test_single_file_scope_when_no_importers(self):
        with tempfile.TemporaryDirectory() as td:
            target = str(Path(td) / "only.py")
            Path(target).touch()

            state: GraphState = {
                "task": "add docstring",
                "target_files": [target],
                "repo_path": td,
                "repo_sha": "abc123",
                "graph_path": None,
            }
            snapshot = _make_snapshot([])
            with patch("src.graph.nodes.dependency_analyzer.AstIndexer") as mock_cls:
                mock_cls.return_value.build_snapshot.return_value = snapshot
                from src.graph.nodes.dependency_analyzer import dependency_analyzer_node
                result = await dependency_analyzer_node(state, RunContext.new())

        assert result["plan_scope"] == "single_file"
        assert result["affected_files"] == [target]

    async def test_multi_file_scope_when_importer_exists(self):
        with tempfile.TemporaryDirectory() as td:
            definition = str(Path(td) / "definition.py")
            importer = str(Path(td) / "importer.py")
            Path(definition).touch()
            Path(importer).touch()

            state: GraphState = {
                "task": "rename function",
                "target_files": [definition],
                "repo_path": td,
                "repo_sha": "abc123",
                "graph_path": None,
            }
            snapshot = _make_snapshot([(importer, definition)])
            with patch("src.graph.nodes.dependency_analyzer.AstIndexer") as mock_cls:
                mock_cls.return_value.build_snapshot.return_value = snapshot
                from src.graph.nodes.dependency_analyzer import dependency_analyzer_node
                result = await dependency_analyzer_node(state, RunContext.new())

        assert result["plan_scope"] == "multi_file"
        assert definition in result["affected_files"]
        assert importer in result["affected_files"]

    async def test_returns_planner_error_when_no_target_files(self):
        state: GraphState = {
            "task": "rename function",
            "target_files": [],
            "repo_path": "/tmp",
            "repo_sha": "",
            "graph_path": None,
        }
        from src.graph.nodes.dependency_analyzer import dependency_analyzer_node
        result = await dependency_analyzer_node(state, RunContext.new())
        assert "planner_error" in result

    async def test_nonexistent_importers_filtered_out(self):
        """Files discovered as importers that don't exist on disk are excluded."""
        with tempfile.TemporaryDirectory() as td:
            definition = str(Path(td) / "definition.py")
            ghost = str(Path(td) / "ghost.py")  # won't be created
            Path(definition).touch()

            state: GraphState = {
                "task": "rename",
                "target_files": [definition],
                "repo_path": td,
                "repo_sha": "",
                "graph_path": None,
            }
            snapshot = _make_snapshot([(ghost, definition)])
            with patch("src.graph.nodes.dependency_analyzer.AstIndexer") as mock_cls:
                mock_cls.return_value.build_snapshot.return_value = snapshot
                from src.graph.nodes.dependency_analyzer import dependency_analyzer_node
                result = await dependency_analyzer_node(state, RunContext.new())

        assert ghost not in result["affected_files"]
        assert result["plan_scope"] == "single_file"
