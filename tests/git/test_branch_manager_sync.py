"""Tests for ensure_repo_synced() in src/git/branch_manager.py."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from git.exc import GitCommandError

from src.git.branch_manager import ensure_repo_synced


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.is_dirty.return_value = False
    repo.remotes.origin.pull.return_value = None
    return repo


class TestEnsureRepoSynced:
    def test_clones_when_path_missing(self, tmp_path):
        missing = str(tmp_path / "not_here")
        with patch("src.git.branch_manager.clone_if_missing") as mock_clone:
            ensure_repo_synced("https://example.com/repo.git", missing, "main")
        mock_clone.assert_called_once_with(
            "https://example.com/repo.git", missing, "", ""
        )

    def test_clones_with_credentials_when_path_missing(self, tmp_path):
        missing = str(tmp_path / "not_here")
        with patch("src.git.branch_manager.clone_if_missing") as mock_clone:
            ensure_repo_synced(
                "https://example.com/repo.git", missing, "main", username="user", token="tok"
            )
        mock_clone.assert_called_once_with(
            "https://example.com/repo.git", missing, "user", "tok"
        )

    def test_checkout_and_pull_when_path_exists_and_clean(self, tmp_path, mock_repo):
        existing = str(tmp_path)
        with (
            patch("src.git.branch_manager._open_repo", return_value=mock_repo),
        ):
            ensure_repo_synced("https://example.com/repo.git", existing, "main")

        mock_repo.git.checkout.assert_called_once_with("main")
        mock_repo.remotes.origin.pull.assert_called_once_with("main")

    def test_skips_checkout_pull_when_dirty(self, tmp_path, mock_repo):
        mock_repo.is_dirty.return_value = True
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            ensure_repo_synced("https://example.com/repo.git", existing, "main")

        mock_repo.git.checkout.assert_not_called()
        mock_repo.remotes.origin.pull.assert_not_called()

    def test_pull_error_is_logged_not_raised(self, tmp_path, mock_repo):
        mock_repo.remotes.origin.pull.side_effect = GitCommandError("pull", 1)
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            # Should not raise
            ensure_repo_synced("https://example.com/repo.git", existing, "main")

    def test_checkout_error_is_logged_not_raised(self, tmp_path, mock_repo):
        mock_repo.git.checkout.side_effect = GitCommandError("checkout", 1)
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            # Should not raise; pull is still attempted
            ensure_repo_synced("https://example.com/repo.git", existing, "main")

        mock_repo.remotes.origin.pull.assert_called_once_with("main")

    def test_uses_specified_branch(self, tmp_path, mock_repo):
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            ensure_repo_synced("https://example.com/repo.git", existing, "develop")

        mock_repo.git.checkout.assert_called_once_with("develop")
        mock_repo.remotes.origin.pull.assert_called_once_with("develop")


class TestSyncRepoMethod:
    """Tests for EmbeddingPipeline._sync_repo() integration."""

    def _make_config(self, **overrides):
        from src.pipeline.contracts import (
            BatchSizeConfig,
            ConcurrencyConfig,
            LimitsConfig,
            Neo4jConfig,
            PipelineConfig,
            SimilarityConfig,
        )

        defaults = dict(
            repo_path="/some/path",
            repo_name="test-repo",
            supported_languages=["python"],
            ignore_paths=[],
            embedding_model="nomic",
            embedding_url="http://localhost:11434",
            allow_gpu=False,
            chat_model="qwen",
            describer_model="qwen",
            similarity=SimilarityConfig(),
            neo4j=Neo4jConfig(uri="bolt://localhost", database="neo4j", username="neo4j", password="pass"),
        )
        defaults.update(overrides)
        return PipelineConfig(**defaults)

    def test_skips_sync_when_no_repo_url(self):
        from src.pipeline.pipeline import EmbeddingPipeline

        config = self._make_config(repo_url="")
        pipeline = EmbeddingPipeline.__new__(EmbeddingPipeline)
        pipeline._config = config

        with patch("src.git.branch_manager.ensure_repo_synced") as mock_sync:
            pipeline._sync_repo()

        mock_sync.assert_not_called()

    def test_calls_ensure_repo_synced_with_git_sync_path(self):
        from src.pipeline.pipeline import EmbeddingPipeline

        config = self._make_config(
            repo_url="https://example.com/repo.git",
            base_branch="main",
            git_sync_path="/canonical/path",
            git_username="user",
            git_token="tok",
        )
        pipeline = EmbeddingPipeline.__new__(EmbeddingPipeline)
        pipeline._config = config

        with patch("src.git.branch_manager.ensure_repo_synced") as mock_sync:
            pipeline._sync_repo()

        mock_sync.assert_called_once_with(
            "https://example.com/repo.git", "/canonical/path", "main", "user", "tok"
        )

    def test_falls_back_to_repo_path_when_git_sync_path_empty(self):
        from src.pipeline.pipeline import EmbeddingPipeline

        config = self._make_config(
            repo_url="https://example.com/repo.git",
            base_branch="main",
            git_sync_path="",
            repo_path="/fallback/path",
        )
        pipeline = EmbeddingPipeline.__new__(EmbeddingPipeline)
        pipeline._config = config

        with patch("src.git.branch_manager.ensure_repo_synced") as mock_sync:
            pipeline._sync_repo()

        mock_sync.assert_called_once_with(
            "https://example.com/repo.git", "/fallback/path", "main", "", ""
        )
