"""Tests for ensure_repo_synced() in src/git/branch_manager.py."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from git.exc import GitCommandError

from src.git.branch_manager import SyncResult, ensure_repo_synced


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.is_dirty.return_value = False
    repo.remotes.origin.pull.return_value = None
    repo.head.commit.hexsha = "abc1234def5678"
    return repo


class TestEnsureRepoSynced:
    def test_clones_when_path_missing(self, tmp_path):
        missing = str(tmp_path / "not_here")
        cloned_repo = MagicMock()
        cloned_repo.head.commit.hexsha = "aabbccdd1234567"
        with patch("src.git.branch_manager.clone_if_missing", return_value=cloned_repo) as mock_clone:
            result = ensure_repo_synced("https://example.com/repo.git", missing, "main")
        mock_clone.assert_called_once_with(
            "https://example.com/repo.git", missing, ""
        )
        assert isinstance(result, SyncResult)
        assert result.operation == "clone"
        assert result.success is True
        assert result.branch == "main"
        assert result.commit_hash == "aabbccd"

    def test_clones_with_credentials_when_path_missing(self, tmp_path):
        missing = str(tmp_path / "not_here")
        cloned_repo = MagicMock()
        cloned_repo.head.commit.hexsha = "aabbccdd1234567"
        with patch("src.git.branch_manager.clone_if_missing", return_value=cloned_repo) as mock_clone:
            ensure_repo_synced(
                "https://example.com/repo.git", missing, "main", token="tok"
            )
        mock_clone.assert_called_once_with(
            "https://example.com/repo.git", missing, "tok"
        )

    def test_checkout_and_pull_when_path_exists_and_clean(self, tmp_path, mock_repo):
        existing = str(tmp_path)
        with (
            patch("src.git.branch_manager._open_repo", return_value=mock_repo),
        ):
            result = ensure_repo_synced("https://example.com/repo.git", existing, "main")

        mock_repo.git.checkout.assert_called_once_with("main")
        mock_repo.remotes.origin.pull.assert_called_once_with("main")
        assert isinstance(result, SyncResult)
        assert result.operation == "pull"
        assert result.success is True
        assert result.branch == "main"

    def test_skips_checkout_pull_when_dirty(self, tmp_path, mock_repo):
        mock_repo.is_dirty.return_value = True
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            result = ensure_repo_synced("https://example.com/repo.git", existing, "main")

        mock_repo.git.checkout.assert_not_called()
        mock_repo.remotes.origin.pull.assert_not_called()
        assert isinstance(result, SyncResult)
        assert result.operation == "skipped"
        assert result.success is True

    def test_pull_error_returns_failed_sync_result(self, tmp_path, mock_repo):
        mock_repo.remotes.origin.pull.side_effect = GitCommandError("pull", 1)
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            result = ensure_repo_synced("https://example.com/repo.git", existing, "main")

        assert isinstance(result, SyncResult)
        assert result.operation == "pull"
        assert result.success is False
        assert result.error is not None

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
            result = ensure_repo_synced("https://example.com/repo.git", existing, "develop")

        mock_repo.git.checkout.assert_called_once_with("develop")
        mock_repo.remotes.origin.pull.assert_called_once_with("develop")
        assert result.branch == "develop"

    def test_pull_uses_authenticated_url_when_token_provided(self, tmp_path, mock_repo):
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            ensure_repo_synced(
                "https://example.com/repo.git", existing, "main", token="tok"
            )
        mock_repo.git.pull.assert_called_once_with(
            "https://x-access-token:tok@example.com/repo.git", "main"
        )
        mock_repo.remotes.origin.pull.assert_not_called()

    def test_already_up_to_date_when_commit_unchanged(self, tmp_path, mock_repo):
        # Same hexsha before and after pull → already_up_to_date=True
        mock_repo.head.commit.hexsha = "abc1234def5678"
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            result = ensure_repo_synced("https://example.com/repo.git", existing, "main")

        assert result.already_up_to_date is True

    def test_not_up_to_date_when_commit_changed(self, tmp_path, mock_repo):
        # Simulate commit advancing after pull by changing hexsha after pull call
        hexsha_values = iter(["aaaaaaa1234567", "bbbbbbb1234567"])

        type(mock_repo.head.commit).hexsha = property(lambda self: next(hexsha_values))
        existing = str(tmp_path)
        with patch("src.git.branch_manager._open_repo", return_value=mock_repo):
            result = ensure_repo_synced("https://example.com/repo.git", existing, "main")

        assert result.already_up_to_date is False


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
        return PipelineConfig(**defaults)  # type: ignore[arg-type]

    def test_skips_sync_when_no_repo_url(self):
        from src.pipeline.pipeline import EmbeddingPipeline

        config = self._make_config(repo_url="")
        pipeline = EmbeddingPipeline.__new__(EmbeddingPipeline)
        pipeline._config = config

        with patch("src.git.branch_manager.ensure_repo_synced") as mock_sync:
            result = pipeline._sync_repo()

        mock_sync.assert_not_called()
        assert result is None

    def test_calls_ensure_repo_synced_with_git_sync_path(self):
        from src.pipeline.pipeline import EmbeddingPipeline

        config = self._make_config(
            repo_url="https://example.com/repo.git",
            base_branch="main",
            git_sync_path="/canonical/path",
            git_token="tok",
        )
        pipeline = EmbeddingPipeline.__new__(EmbeddingPipeline)
        pipeline._config = config

        with patch("src.git.branch_manager.ensure_repo_synced") as mock_sync:
            pipeline._sync_repo()

        mock_sync.assert_called_once_with(
            "https://example.com/repo.git", "/canonical/path", "main", "tok"
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
            "https://example.com/repo.git", "/fallback/path", "main", ""
        )
