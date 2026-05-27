import subprocess
import tempfile
import unittest
from pathlib import Path

from src.runtime.state import (
    assert_clean_repository,
    capture_repository_state,
    get_repository_revision,
    is_repository_clean,
    restore_repository_state,
)


def _git(repository_path: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=repository_path, check=True, capture_output=True, text=True)


class TestRuntimeState(unittest.TestCase):
    def test_revision_capture_and_dirty_detection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")

            revision = get_repository_revision(repo_path)
            self.assertEqual(len(revision), 40)
            self.assertTrue(is_repository_clean(repo_path))

            state = capture_repository_state(repo_path)
            self.assertEqual(state.repository_revision, revision)
            self.assertTrue(state.is_clean)

            tracked.write_text("changed\n", encoding="utf-8")
            self.assertFalse(is_repository_clean(repo_path))
            with self.assertRaises(RuntimeError):
                assert_clean_repository(repo_path)

    def test_restore_repository_state_discards_changes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            _git(repo_path, "init")
            _git(repo_path, "config", "user.email", "test@example.com")
            _git(repo_path, "config", "user.name", "Test User")

            tracked = repo_path / "tracked.txt"
            tracked.write_text("hello\n", encoding="utf-8")
            _git(repo_path, "add", "tracked.txt")
            _git(repo_path, "commit", "-m", "initial")

            tracked.write_text("changed\n", encoding="utf-8")
            untracked = repo_path / "temp.txt"
            untracked.write_text("temp\n", encoding="utf-8")

            restore_repository_state(repo_path)

            self.assertTrue(is_repository_clean(repo_path))
            self.assertEqual(tracked.read_text(encoding="utf-8"), "hello\n")
            self.assertFalse(untracked.exists())
