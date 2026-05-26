"""Simple, deterministic repository indexer implementation.

This indexer is intentionally small and isolated for Phase 2 Step 3.
It uses the Python stdlib `ast` module only and produces a
`RepositorySnapshot` from `src.repository.types`.

Constraints enforced:
- AST parsing only (no runtime execution)
- Deterministic directory/file ordering
- Safely handle malformed Python files
- No graph or LLM interactions
"""

from __future__ import annotations

import ast
import os
from typing import List

from src.repository.types import Symbol, DependencyEdge, FileNode, RepositorySnapshot


IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", ".mypy_cache"}


class SimpleRepositoryIndexer:
    """Concrete indexer producing a RepositorySnapshot for a given root."""

    def build_snapshot(self, root_path: str) -> RepositorySnapshot:
        files: List[FileNode] = []
        edges: List[DependencyEdge] = []

        # Walk deterministically: sort directories and filenames
        for dirpath, dirnames, filenames in os.walk(root_path):
            # prune ignored directories in-place to keep os.walk deterministic
            dirnames[:] = [d for d in sorted(dirnames) if d not in IGNORED_DIRS]

            for fname in sorted(filenames):
                if not fname.endswith(".py"):
                    continue

                full_path = os.path.normpath(os.path.join(dirpath, fname))
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0

                try:
                    with open(full_path, "r", encoding="utf-8") as fh:
                        src = fh.read()
                    node = ast.parse(src)
                except Exception:
                    # Malformed file: include entry with empty symbols/imports
                    files.append(FileNode(path=full_path, language="python", size=size, symbols=[], imports=[]))
                    continue

                symbols: List[Symbol] = []
                imports: List[str] = []

                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        symbols.append(Symbol(name=child.name, kind="function", lineno=getattr(child, "lineno", None), docstring=ast.get_docstring(child)))
                    elif isinstance(child, ast.ClassDef):
                        symbols.append(Symbol(name=child.name, kind="class", lineno=getattr(child, "lineno", None), docstring=ast.get_docstring(child)))
                        # collect methods
                        for m in [n for n in child.body if isinstance(n, ast.FunctionDef)]:
                            symbols.append(Symbol(name=f"{child.name}.{m.name}", kind="method", lineno=getattr(m, "lineno", None), docstring=ast.get_docstring(m)))
                    elif isinstance(child, ast.Import):
                        for alias in child.names:
                            imports.append(alias.name)
                    elif isinstance(child, ast.ImportFrom):
                        module = child.module or ""
                        imports.append(module)

                # sort symbols and imports deterministically
                symbols = sorted(symbols, key=lambda s: (s.name, s.kind))
                imports = sorted(set([i for i in imports if i]))

                files.append(FileNode(path=full_path, language="python", size=size, symbols=symbols, imports=imports))

                # create shallow dependency edges (to_path holds module name for now)
                for imp in imports:
                    edges.append(DependencyEdge(from_path=full_path, to_path=imp, import_text=imp))

        # sort files deterministically by path
        files = sorted(files, key=lambda f: f.path)
        edges = sorted(edges, key=lambda e: (e.from_path, e.to_path))

        return RepositorySnapshot(files=files, edges=edges)

    def get_file_symbols(self, snapshot: RepositorySnapshot, file_path: str) -> List[Symbol]:
        f = snapshot.get_file(file_path)
        return f.symbols if f is not None else []

    def get_dependencies(self, snapshot: RepositorySnapshot, file_path: str) -> List[DependencyEdge]:
        return [e for e in snapshot.edges if e.from_path == file_path]
