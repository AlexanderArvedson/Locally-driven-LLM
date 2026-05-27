from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
from typing import Iterator


_REPO_ROOT = Path(__file__).resolve().parents[2]


def copy_fixture_repo_to(tmp_dir: str | Path, fixture_name: str = "repo_simple") -> Path:
    """Copy a named fixture repo into `tmp_dir` and return the copied path."""
    src = _REPO_ROOT / "tests" / "fixtures" / fixture_name
    dest = Path(tmp_dir) / fixture_name
    shutil.copytree(src, dest)
    return dest


@contextmanager
def temporary_fixture_repo(fixture_name: str = "repo_simple") -> Iterator[Path]:
    """Context manager that yields a temporary copy of a fixture repository.

    Example:
        with temporary_fixture_repo() as repo_path:
            # use repo_path (Path) inside test
    """
    with tempfile.TemporaryDirectory() as td:
        yield copy_fixture_repo_to(td, fixture_name)
