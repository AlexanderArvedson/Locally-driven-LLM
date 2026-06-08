"""Repository file scanner.

Walks a source tree and yields paths to source files whose extension
matches a configured language set, while skipping any paths that match
the configured ignore list.
"""

from __future__ import annotations

import os
from pathlib import Path

_LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
}


def _supported_extensions(languages: list[str]) -> frozenset[str]:
    exts: list[str] = []
    for lang in languages:
        exts.extend(_LANGUAGE_EXTENSIONS.get(lang.lower(), []))
    return frozenset(exts)


def _is_ignored(path: Path, repo_root: Path, ignore_names: list[str]) -> bool:
    """Return True if the path relative to repo_root matches any ignore pattern.

    Single-part patterns (e.g. ``node_modules``) match any path component.
    Multi-part patterns (e.g. ``dal/models``) match a consecutive segment.
    """
    try:
        rel = path.relative_to(repo_root)
    except ValueError:
        return False
    parts = rel.parts
    for pattern in ignore_names:
        pattern_parts = Path(pattern).parts
        if len(pattern_parts) == 1:
            if pattern_parts[0] in parts:
                return True
        else:
            n = len(pattern_parts)
            if any(parts[i:i + n] == pattern_parts for i in range(len(parts) - n + 1)):
                return True
    return False


def scan_repository(
    repo_path: str | Path,
    supported_languages: list[str],
    ignore_paths: list[str],
) -> list[Path]:
    """Return sorted list of source file paths to process.

    Args:
        repo_path: Root directory of the repository to scan.
        supported_languages: Language names to include (e.g. ``["python", "typescript"]``).
        ignore_paths: Directory/file name segments to skip (e.g. ``[".venv", "node_modules"]``).
    """
    root = Path(repo_path).resolve()
    extensions = _supported_extensions(supported_languages)
    results: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        # Prune ignored directories in-place so os.walk skips their contents.
        dirnames[:] = [
            d for d in dirnames
            if not _is_ignored(current / d, root, ignore_paths)
        ]

        for filename in filenames:
            file_path = current / filename
            if file_path.suffix in extensions and not _is_ignored(file_path, root, ignore_paths):
                results.append(file_path)

    return sorted(results)
