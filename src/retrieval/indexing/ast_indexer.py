"""AST-based repository indexer.

Produces a RepositorySnapshot by walking the repository and parsing every
Python file with the stdlib `ast` module. Deterministic: directories and
files are visited in sorted order; malformed files are included with empty
symbols/imports rather than skipped entirely.
"""

from __future__ import annotations

import ast
import os
from typing import List

from src.retrieval.contracts.types import Symbol, DependencyEdge, FileNode, RepositorySnapshot


IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", ".mypy_cache"}


class AstIndexer:
    """Concrete indexer producing a RepositorySnapshot for a given root."""

    def build_snapshot(self, root_path: str) -> RepositorySnapshot:
        files: List[FileNode] = []
        edges: List[DependencyEdge] = []

        for dirpath, dirnames, filenames in os.walk(root_path):
            # Prune ignored directories in-place to keep os.walk deterministic.
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
                    files.append(FileNode(path=full_path, language="python", size=size, symbols=[], imports=[]))
                    continue

                symbols: List[Symbol] = []
                imports: List[str] = []

                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        symbols.append(Symbol(name=child.name, kind="function", lineno=getattr(child, "lineno", None), docstring=ast.get_docstring(child)))
                    elif isinstance(child, ast.ClassDef):
                        symbols.append(Symbol(name=child.name, kind="class", lineno=getattr(child, "lineno", None), docstring=ast.get_docstring(child)))
                        for m in [n for n in child.body if isinstance(n, ast.FunctionDef)]:
                            symbols.append(Symbol(name=f"{child.name}.{m.name}", kind="method", lineno=getattr(m, "lineno", None), docstring=ast.get_docstring(m)))
                    elif isinstance(child, ast.Import):
                        for alias in child.names:
                            imports.append(alias.name)
                    elif isinstance(child, ast.ImportFrom):
                        module = child.module or ""
                        imports.append(module)

                symbols = sorted(symbols, key=lambda s: (s.name, s.kind))
                imports = sorted(set([i for i in imports if i]))

                files.append(FileNode(path=full_path, language="python", size=size, symbols=symbols, imports=imports))

                for imp in imports:
                    edges.append(DependencyEdge(from_path=full_path, to_path=imp, import_text=imp))

        files = sorted(files, key=lambda f: f.path)
        edges = sorted(edges, key=lambda e: (e.from_path, e.to_path))

        return RepositorySnapshot(files=files, edges=edges)

    def get_file_symbols(self, snapshot: RepositorySnapshot, file_path: str) -> List[Symbol]:
        """Return Symbol list for a file from the snapshot."""
        f = snapshot.get_file(file_path)
        return f.symbols if f is not None else []

    def get_dependencies(self, snapshot: RepositorySnapshot, file_path: str) -> List[DependencyEdge]:
        """Return outgoing DependencyEdge list for a file from the snapshot."""
        return [e for e in snapshot.edges if e.from_path == file_path]
