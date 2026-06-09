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

from tree_sitter import Parser

from src.pipeline.contracts import FunctionRecord, PipelineConfig
from src.pipeline.extraction.scanner import scan_repository
from src.pipeline.extraction.treesitter import (
    _EXT_LANGUAGE,
    _FUNC_TYPES_BY_LANG,
    _NAME_NODE_TYPES,
    _PY_FUNC_TYPES,
    _PY_LANGUAGE,
    _TS_FUNC_TYPES,
    _find_functions,
    _get_class_name,
    _get_name_token,
    _get_ts_language,
    _get_tsx_language,
    _is_anonymous_context,
    _resolve_name_from_context,
)


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


def _is_anonymous_callback_name(name: str) -> bool:
    """Return True for synthetically-named callbacks like useEffect$0@L87 or map@L42.

    The ``@L<line>`` suffix is appended by the extractor whenever a function has
    no developer-assigned name and is resolved only from its call-expression
    context. Real identifiers in TypeScript/JavaScript/Python cannot contain ``@``.

    Truly unresolvable functions (``<anonymous>``) are caught separately via the
    ``is_anonymous`` flag in the extraction loop rather than by this helper.
    """
    return "@L" in name


def _extract_from_file(
    file_path: Path,
    repo_root: Path,
    repo_name: str,
    language_name: str,
    func_types: frozenset[str],
    parser: Parser,
    test_patterns: list[str] | None = None,
    ignore_anonymous_callbacks: bool = True,
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
        # Try direct name token first, then fall back to context resolution.
        # Callbacks (call-expression args, JSX handlers, export default) get a
        # location-suffixed name (e.g. forEach@L42) so each occurrence is
        # unique in the graph. Only truly unresolvable functions stay <anonymous>.
        function_name = _get_name_token(fn_node)
        if function_name is None:
            is_anonymous = _is_anonymous_context(fn_node)
            resolved = _resolve_name_from_context(fn_node)
            if resolved is None:
                function_name = "<anonymous>"
                is_anonymous = True
            elif is_anonymous:
                start_line = fn_node.start_point[0] + 1
                label = file_path.stem if resolved == "default" else resolved
                function_name = f"{label}@L{start_line}"
                is_anonymous = False
            else:
                function_name = resolved
                is_anonymous = False
        else:
            is_anonymous = False

        if ignore_anonymous_callbacks and (_is_anonymous_callback_name(function_name) or is_anonymous):
            continue

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
            is_anonymous=is_anonymous,
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
                tsx_lang = _get_tsx_language()
                func_types = _FUNC_TYPES_BY_LANG[lang]
                # .ts/.js use the TypeScript grammar; .tsx/.jsx need the TSX
                # grammar which adds JSX node types (jsx_element, jsx_attribute…)
                for ext in (".ts", ".js"):
                    parsers[ext] = (Parser(ts_lang), func_types)
                for ext in (".tsx", ".jsx"):
                    parsers[ext] = (Parser(tsx_lang), func_types)

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
                    ignore_anonymous_callbacks=self._config.ignore_anonymous_callbacks,
                )
            )

        return records
