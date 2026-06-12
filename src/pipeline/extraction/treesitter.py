"""Tree-sitter language setup and AST traversal helpers.

Provides lazily-loaded language grammars, function-type constants, and node
traversal utilities shared by the function extractor.
"""

from __future__ import annotations

from tree_sitter import Language, Node
import tree_sitter_python as tspython

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
    """Return the text of the name field of *node*, if present.

    Uses the tree-sitter named 'name' field rather than scanning all children,
    which prevents single-param arrow functions (``resolve => ...``) from
    having their parameter identifier mistaken for a function name.
    """
    name_node = node.child_by_field_name("name")
    if name_node is not None and name_node.type in _NAME_NODE_TYPES:
        return name_node.text.decode("utf-8") if name_node.text else None
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
