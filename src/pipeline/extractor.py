"""Function extractor.

Uses tree-sitter directly to walk the AST of each source file and extract
every function or method as a ``FunctionRecord``. No slicer abstraction is
needed here because the goal is enumeration (all nodes), not lookup-by-name.

Tree-sitter nodes expose ``start_point`` / ``end_point`` (0-indexed row, col)
and ``start_byte`` / ``end_byte``, so source text and line numbers are read
directly from node attributes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tree_sitter import Language, Node, Parser
import tree_sitter_python as tspython

from src.pipeline.contracts import FunctionRecord, PipelineConfig
from src.pipeline.scanner import scan_repository

# ---------------------------------------------------------------------------
# Language setup
# ---------------------------------------------------------------------------

_PY_LANGUAGE = Language(tspython.language())

# TypeScript grammar — imported lazily so the package is only required when
# TypeScript files are actually present.
def _get_ts_language() -> Language:
    try:
        import tree_sitter_typescript as tsts
        return Language(tsts.language_typescript())
    except ImportError as e:
        raise ImportError(
            "tree-sitter-typescript is required for TypeScript extraction. "
            "Install it with: pip install tree-sitter-typescript"
        ) from e


# Maps file extensions to (Language, language_name) tuples.
_EXT_LANGUAGE: dict[str, tuple[Language | None, str]] = {
    ".py": (_PY_LANGUAGE, "python"),
    ".ts": (None, "typescript"),   # resolved lazily
    ".tsx": (None, "typescript"),
    ".js": (None, "javascript"),
    ".jsx": (None, "javascript"),
}

# Python node types that define a function or method.
_PY_FUNC_TYPES = frozenset({"function_definition", "async_function_definition"})

# TypeScript/JavaScript node types that define a function or method.
_TS_FUNC_TYPES = frozenset({
    "function_declaration",
    "function",
    "method_definition",
    "arrow_function",
    "generator_function_declaration",
    "generator_function",
})

_FUNC_TYPES_BY_LANG: dict[str, frozenset[str]] = {
    "python": _PY_FUNC_TYPES,
    "typescript": _TS_FUNC_TYPES,
    "javascript": _TS_FUNC_TYPES,
}


# ---------------------------------------------------------------------------
# AST traversal helpers
# ---------------------------------------------------------------------------

def _find_functions(node: Node, func_types: frozenset[str]) -> list[Node]:
    """Recursively collect all function/method nodes in the subtree."""
    results: list[Node] = []
    if node.type in func_types:
        results.append(node)
    for child in node.children:
        results.extend(_find_functions(child, func_types))
    return results


def _get_identifier(node: Node) -> str | None:
    """Return the text of the first ``identifier`` child of a node."""
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8") if child.text else None
    return None


def _get_class_name(node: Node) -> str | None:
    """Walk ancestors to find an enclosing class definition and return its name."""
    parent = node.parent
    while parent is not None:
        if parent.type in ("class_definition", "class_declaration"):
            return _get_identifier(parent)
        parent = parent.parent
    return None


def _get_property_name(node: Node) -> str | None:
    """For TS property assignments (``foo = () => ...``), return the property name."""
    parent = node.parent
    if parent is None:
        return None
    # arrow_function assigned to a variable: variable_declarator → identifier
    if parent.type == "variable_declarator":
        return _get_identifier(parent)
    # class property: public_field_definition or property_signature
    if parent.type in ("public_field_definition", "property_identifier"):
        return _get_identifier(parent)
    return None


def _record_id(repo: str, file_path: str, qualified_name: str, start_line: int) -> str:
    key = f"{repo}:{file_path}:{qualified_name}:{start_line}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _source_hash(source_code: str) -> str:
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Per-file extraction
# ---------------------------------------------------------------------------

def _is_test_file(rel_path: str, test_patterns: list[str]) -> bool:
    """Return True if the relative path matches any configured test pattern."""
    return any(pattern in rel_path for pattern in test_patterns)


def _extract_from_file(
    file_path: Path,
    repo_root: Path,
    repo_name: str,
    language_name: str,
    func_types: frozenset[str],
    parser: Parser,
    test_patterns: list[str] | None = None,
) -> list[FunctionRecord]:
    try:
        source_bytes = file_path.read_bytes()
    except OSError:
        return []

    try:
        tree = parser.parse(source_bytes)
    except Exception:
        return []

    rel_path = str(file_path.relative_to(repo_root))
    is_test = _is_test_file(rel_path, test_patterns or [])
    records: list[FunctionRecord] = []

    for fn_node in _find_functions(tree.root_node, func_types):
        # Determine function name
        function_name = _get_identifier(fn_node)
        if function_name is None:
            # Anonymous arrow function: try parent context
            function_name = _get_property_name(fn_node) or "<anonymous>"

        class_name = _get_class_name(fn_node)
        qualified_name = f"{class_name}.{function_name}" if class_name else function_name

        start_line = fn_node.start_point[0] + 1   # tree-sitter rows are 0-indexed
        end_line = fn_node.end_point[0] + 1

        source_code = source_bytes[fn_node.start_byte:fn_node.end_byte].decode("utf-8", errors="replace")

        records.append(FunctionRecord(
            id=_record_id(repo_name, rel_path, qualified_name, start_line),
            repo=repo_name,
            language=language_name,
            file_path=rel_path,
            function_name=function_name,
            qualified_name=qualified_name,
            class_name=class_name,
            start_line=start_line,
            end_line=end_line,
            source_code=source_code,
            source_hash=_source_hash(source_code),
            is_test=is_test,
        ))

    return records


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class FunctionExtractor:
    """Extracts every function and method from a repository as FunctionRecords.

    Embeddings and descriptions are left as ``None`` — they are filled by
    downstream pipeline stages.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._repo_root = Path(config.repo_path).resolve()

    def extract_all(self) -> list[FunctionRecord]:
        """Return one FunctionRecord per function/method found in the repository."""
        files = scan_repository(
            self._config.repo_path,
            self._config.supported_languages,
            self._config.ignore_paths,
        )

        # Build parsers per language (lazy TS grammar init)
        parsers: dict[str, tuple[Parser, frozenset[str]]] = {}
        for lang in set(self._config.supported_languages):
            lang = lang.lower()
            if lang == "python":
                p = Parser(_PY_LANGUAGE)
                parsers["python"] = (p, _PY_FUNC_TYPES)
                parsers[".py"] = (p, _PY_FUNC_TYPES)
            elif lang in ("typescript", "javascript"):
                ts_lang = _get_ts_language()
                p = Parser(ts_lang)
                func_types = _FUNC_TYPES_BY_LANG[lang]
                for ext in (".ts", ".tsx", ".js", ".jsx"):
                    parsers[ext] = (p, func_types)

        records: list[FunctionRecord] = []
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext not in parsers:
                continue
            parser, func_types = parsers[ext]
            lang_name = _EXT_LANGUAGE.get(ext, (None, ext.lstrip(".")))[1]
            records.extend(
                _extract_from_file(
                    file_path,
                    self._repo_root,
                    self._config.repo_name,
                    lang_name,
                    func_types,
                    parser,
                    test_patterns=self._config.test_patterns,
                )
            )

        return records
