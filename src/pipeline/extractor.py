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

# TypeScript grammars — imported lazily so the package is only required when
# TypeScript files are actually present.
# .ts/.js  → language_typescript()  (no JSX)
# .tsx/.jsx → language_tsx()         (includes JSX node types)
def _get_ts_language() -> Language:
    try:
        import tree_sitter_typescript as tsts
        return Language(tsts.language_typescript())
    except ImportError as e:
        raise ImportError(
            "tree-sitter-typescript is required for TypeScript extraction. "
            "Install it with: pip install tree-sitter-typescript"
        ) from e


def _get_tsx_language() -> Language:
    try:
        import tree_sitter_typescript as tsts
        return Language(tsts.language_tsx())
    except ImportError as e:
        raise ImportError(
            "tree-sitter-typescript is required for TSX extraction. "
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
    "function_expression",   # anonymous / named function expressions: const f = function() {}
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

# Node types that carry a name token across all supported languages.
# - identifier              plain names in Python, JS/TS function declarations
# - property_identifier     TS/JS method names, object keys
# - type_identifier         TS class / type names
# - private_property_identifier  TS private class members (#foo)
_NAME_NODE_TYPES = frozenset({
    "identifier",
    "property_identifier",
    "type_identifier",
    "private_property_identifier",
})


# ---------------------------------------------------------------------------
# AST traversal helpers
# ---------------------------------------------------------------------------

def _find_functions(node: Node, func_types: frozenset[str]) -> list[Node]:
    """Recursively collect all function/method nodes in the subtree."""
    results: list[Node] = []
    # is_named distinguishes real function nodes from same-string keyword tokens
    # (e.g. the bare "function" keyword inside function_declaration is is_named=False)
    if node.type in func_types and node.is_named:
        results.append(node)
    for child in node.children:
        results.extend(_find_functions(child, func_types))
    return results


def _get_name_token(node: Node) -> str | None:
    """Return the text of the first name-bearing child of *node*.

    Covers Python identifiers, TypeScript/JS method names
    (property_identifier), TypeScript class/type names (type_identifier), and
    TypeScript private class members (private_property_identifier).
    """
    for child in node.children:
        if child.type in _NAME_NODE_TYPES:
            return child.text.decode("utf-8") if child.text else None
    return None


def _get_class_name(node: Node) -> str | None:
    """Walk ancestors to find an enclosing class definition and return its name."""
    parent = node.parent
    while parent is not None:
        if parent.type in ("class_definition", "class_declaration"):
            return _get_name_token(parent)
        parent = parent.parent
    return None


def _resolve_name_from_context(node: Node) -> str | None:
    """Infer a function name from the surrounding AST context.

    Called when the function node itself carries no name token (arrow
    functions, anonymous function expressions, etc.). Handles common patterns
    across Python, TypeScript, and JavaScript:

      Variable declarations    const foo = () => ...
      Class field assignments  class C { foo = () => ... }
      Object literal pairs     { foo: () => ... }
      Assignment expressions   foo = () => ...  /  obj.method = () => ...
      JSX attribute values     <Comp onClick={() => ...} />
      Call-expression args     useEffect(() => ..., [])
      Export default           export default () => ...
    """
    parent = node.parent
    if parent is None:
        return None

    # const/let/var foo = () => ...
    if parent.type == "variable_declarator":
        return _get_name_token(parent)

    # class C { foo = () => ... }
    if parent.type == "public_field_definition":
        return _get_name_token(parent)

    # foo = () => ...  or  obj.method = () => ...
    if parent.type == "assignment_expression":
        left = parent.child_by_field_name("left")
        if left is not None and left.text:
            raw = left.text.decode("utf-8")
            # Take the last segment of a member expression (obj.foo → foo)
            return raw.rsplit(".", 1)[-1]

    # { key: () => ... }  —  object literal pair
    if parent.type == "pair":
        key = parent.child_by_field_name("key")
        if key is not None and key.text and key.type != "computed_property_name":
            return key.text.decode("utf-8").strip("\"'`")

    # <Component onClick={() => ...} />
    if parent.type == "jsx_expression":
        gp = parent.parent
        if gp is not None and gp.type == "jsx_attribute":
            attr = next(
                (c for c in gp.children if c.type in _NAME_NODE_TYPES),
                None,
            )
            if attr is not None and attr.text:
                return attr.text.decode("utf-8")

    # useEffect(() => ..., [])  /  arr.map(item => ...)
    if parent.type == "arguments":
        gp = parent.parent
        if gp is not None and gp.type == "call_expression":
            callee = gp.child_by_field_name("function")
            if callee is None and gp.children:
                callee = gp.children[0]
            if callee is not None and callee.text:
                callee_name = callee.text.decode("utf-8").rsplit(".", 1)[-1]
                # Determine which argument position this node occupies
                fn_args = [
                    c for c in parent.children
                    if c.type not in {",", "(", ")", "comment", "whitespace"}
                ]
                idx = next(
                    (i for i, c in enumerate(fn_args) if c.start_byte == node.start_byte),
                    0,
                )
                # Single-arg callbacks get just the callee name (useEffect),
                # multi-arg calls get a positional suffix (map$0)
                return callee_name if len(fn_args) == 1 else f"{callee_name}${idx}"

    # export default function() {}  /  export default () => {}
    if parent.type in ("export_statement", "export_default_declaration"):
        return "default"

    return None


def _is_anonymous_context(node: Node) -> bool:
    """Return True when the function's name is derived from an anonymous context.

    Names that come from call-expression arguments (``arr.map(fn)``), export
    default declarations (``export default () => {}``), or JSX attribute values
    (``<Comp onClick={() => …} />``) are ephemeral labels, not declared
    identifiers.  Functions with these origins are excluded from SIMILAR_TO edge
    creation so they don't dilute the similarity graph with boilerplate noise.

    Variable bindings (``const foo = () => …``), object-literal keys, class
    field assignments, and assignment expressions all produce real declared names
    and are therefore NOT considered anonymous.
    """
    parent = node.parent
    if parent is None:
        return True

    # arr.map(fn) / setState(prev => ...) / useEffect(() => ..., [])
    if parent.type == "arguments":
        gp = parent.parent
        if gp is not None and gp.type == "call_expression":
            return True

    # export default () => {}  /  export default function() {}
    if parent.type in ("export_statement", "export_default_declaration"):
        return True

    # <Comp onClick={() => ...} />
    if parent.type == "jsx_expression":
        gp = parent.parent
        if gp is not None and gp.type == "jsx_attribute":
            return True

    return False


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
        # Try direct name token first, then fall back to context resolution.
        # Functions that fall back are candidates for is_anonymous — checked
        # by _is_anonymous_context to distinguish real bindings from callbacks.
        function_name = _get_name_token(fn_node)
        if function_name is None:
            is_anonymous = _is_anonymous_context(fn_node)
            function_name = _resolve_name_from_context(fn_node) or "<anonymous>"
            if function_name == "<anonymous>":
                is_anonymous = True
        else:
            is_anonymous = False

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
                )
            )

        return records
