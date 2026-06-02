"""Tests for git branch_manager utilities, including the new commit_files function."""

import os
import tempfile
import unittest
from pathlib import Path

import git


def _init_repo(path: str) -> git.Repo:
    repo = git.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    # Create an initial commit so HEAD exists.
    readme = Path(path) / "README.md"
    readme.write_text("init\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return repo


class TestCommitFiles(unittest.TestCase):
    def test_stages_and_commits_multiple_files(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(td)

            a = Path(td) / "a.py"
            b = Path(td) / "b.py"
            a.write_text("x = 1\n", encoding="utf-8")
            b.write_text("y = 2\n", encoding="utf-8")

            from src.git.branch_manager import commit_files
            sha = commit_files(td, [str(a), str(b)], "AI: rename x")

            assert sha  # non-empty hex SHA
            repo2 = git.Repo(td)
            last = repo2.head.commit
            assert last.hexsha == sha
            assert "a.py" in [blob.path for blob in last.tree.blobs]
            assert "b.py" in [blob.path for blob in last.tree.blobs]

    def test_returns_empty_string_when_nothing_changed(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(td)
            a = Path(td) / "README.md"  # already committed, unchanged

            from src.git.branch_manager import commit_files
            sha = commit_files(td, [str(a)], "AI: no-op")

            assert sha == ""

    def test_partial_list_only_stages_changed_files(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(td)

            unchanged = Path(td) / "README.md"
            changed = Path(td) / "new.py"
            changed.write_text("z = 3\n", encoding="utf-8")

            from src.git.branch_manager import commit_files
            sha = commit_files(td, [str(unchanged), str(changed)], "AI: add new.py")

            assert sha  # commit happened because new.py changed
            repo2 = git.Repo(td)
            committed_paths = [blob.path for blob in repo2.head.commit.tree.blobs]
            assert "new.py" in committed_paths


class TestCommitFile(unittest.TestCase):
    def test_single_file_commit(self):
        with tempfile.TemporaryDirectory() as td:
            _init_repo(td)
            f = Path(td) / "solo.py"
            f.write_text("pass\n", encoding="utf-8")

            from src.git.branch_manager import commit_file
            sha = commit_file(td, str(f), "AI: add solo.py")

            assert sha
            repo = git.Repo(td)
            assert repo.head.commit.hexsha == sha

    def test_unchanged_file_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as td:
            _init_repo(td)
            f = Path(td) / "README.md"

            from src.git.branch_manager import commit_file
            sha = commit_file(td, str(f), "AI: no-op")

            assert sha == ""
