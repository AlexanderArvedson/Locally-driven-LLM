"""Python implementation of LanguageSlicer using tree-sitter.

Uses tree-sitter-python for parsing so the same slicing architecture can be
extended to other languages by implementing the LanguageSlicer Protocol and
registering the file extension in registry.py.
"""

from __future__ import annotations

import tree_sitter_python as _tspython
from tree_sitter import Language, Node, Parser

from src.retrieval.slicing.protocol import LanguageSlicer, SymbolSlice

_PY_LANGUAGE = Language(_tspython.language())

_SYMBOL_TYPES = {"function_definition", "async_function_definition", "class_definition"}
_IMPORT_TYPES = {"import_statement", "import_from_statement"}
_CONTRACT_BASE_NAMES = {"TypedDict", "Protocol", "ABC"}
_DATACLASS_DECORATOR = "dataclass"


def _make_parser() -> Parser:
    return Parser(_PY_LANGUAGE)


class PythonSlicer:
    """LanguageSlicer implementation for Python source files."""

    def extract_symbol(self, source: str, name: str) -> SymbolSlice | None:
        """Return a SymbolSlice for the named function/async function/class.

        Searches module level first, then one level inside any class (for methods).
        Returns None if the symbol is not found or the source cannot be parsed.
        """
        tree = _make_parser().parse(source.encode())
        lines = source.splitlines(keepends=True)
        root = tree.root_node

        node = _find_symbol(root, name)
        if node is None:
            return None

        return _build_slice(node, name, lines)

    def extract_imports_for(self, source: str, symbol_name: str) -> str:
        """Return import lines actually referenced by the named symbol."""
        tree = _make_parser().parse(source.encode())
        root = tree.root_node

        symbol_node = _find_symbol(root, symbol_name)
        if symbol_node is None:
            return ""

        used = _collect_names(symbol_node)
        lines = source.splitlines(keepends=True)
        collected: list[str] = []

        for child in root.children:
            if child.type not in _IMPORT_TYPES:
                continue
            if _import_exposes_used_name(child, used):
                start = child.start_point.row
                end = child.end_point.row
                collected.append("".join(lines[start : end + 1]).rstrip())

        return "\n".join(collected)

    def extract_class_context(self, source: str, method_name: str) -> str | None:
        """If method_name is a method, return its enclosing class header + docstring."""
        tree = _make_parser().parse(source.encode())
        root = tree.root_node
        lines = source.splitlines(keepends=True)

        for child in root.children:
            if child.type != "class_definition":
                continue
            body = child.child_by_field_name("body")
            if body is None:
                continue
            for item in body.children:
                if item.type not in ("function_definition", "async_function_definition"):
                    continue
                name_node = item.child_by_field_name("name")
                if name_node and _node_name(name_node) == method_name:
                    header_line = lines[child.start_point.row].rstrip()
                    docstring = _get_docstring(child)
                    if docstring:
                        short = docstring.splitlines()[0]
                        return f'{header_line}\n    """{short}"""\n    ...'
                    return f"{header_line}\n    ..."
        return None

    def extract_contracts(self, source: str, symbol_name: str) -> str:
        """Return TypedDict/dataclass/Protocol class definitions used by the symbol."""
        tree = _make_parser().parse(source.encode())
        root = tree.root_node

        symbol_node = _find_symbol(root, symbol_name)
        if symbol_node is None:
            return ""

        used = _collect_names(symbol_node)
        lines = source.splitlines(keepends=True)
        parts: list[str] = []

        for child in root.children:
            if child.type != "class_definition":
                continue
            name_node = child.child_by_field_name("name")
            if name_node is None or _node_name(name_node) not in used:
                continue
            if _is_contract(child):
                start = child.start_point.row
                end = child.end_point.row
                parts.append("".join(lines[start : end + 1]).rstrip())

        return "\n\n".join(parts)

    def stitch_symbol(self, original: str, sl: SymbolSlice, modified: str) -> str:
        """Replace the original symbol with modified and return the full file.

        Re-applies the original indentation if the LLM stripped it (e.g. returned
        a module-level function when the original was a method).
        Returns original unchanged when the line range is out of bounds.
        """
        lines = original.splitlines(keepends=True)

        if sl.start_line < 1 or sl.start_line > len(lines) or sl.end_line > len(lines):
            return original

        mod_text = modified.rstrip() + "\n"
        mod_lines = mod_text.splitlines(keepends=True)

        if mod_lines:
            first = mod_lines[0]
            actual_indent = len(first) - len(first.lstrip())
            if actual_indent < sl.indent:
                pad = " " * (sl.indent - actual_indent)
                mod_lines = [pad + ln for ln in mod_lines]

        prefix = lines[: sl.start_line - 1]
        suffix = lines[sl.end_line :]
        return "".join(prefix) + "".join(mod_lines) + "".join(suffix)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _node_name(node: Node) -> str:
    """Return the text of a node's name field, or empty string if absent."""
    return (node.text or b"").decode() if node.text is not None else ""


def _find_symbol(root: Node, name: str) -> Node | None:
    """Find the AST node for name at module level or one class deep."""
    for child in root.children:
        if child.type in _SYMBOL_TYPES:
            name_node = child.child_by_field_name("name")
            if name_node and _node_name(name_node) == name:
                return child

    for child in root.children:
        if child.type != "class_definition":
            continue
        body = child.child_by_field_name("body")
        if body is None:
            continue
        for item in body.children:
            if item.type in ("function_definition", "async_function_definition"):
                name_node = item.child_by_field_name("name")
                if name_node and _node_name(name_node) == name:
                    return item
    return None


def _build_slice(node: Node, name: str, lines: list[str]) -> SymbolSlice:
    """Build a SymbolSlice from a tree-sitter node."""
    # Include decorator lines that appear directly before the node.
    start_row = node.start_point.row
    decorators = node.children_by_field_name("decorator")
    if decorators:
        start_row = decorators[0].start_point.row

    end_row = node.end_point.row  # inclusive, 0-based
    source = "".join(lines[start_row : end_row + 1])
    first_line = lines[start_row]
    indent = len(first_line) - len(first_line.lstrip())

    return SymbolSlice(
        name=name,
        source=source,
        start_line=start_row + 1,   # convert to 1-based
        end_line=end_row + 1,
        indent=indent,
    )


def _collect_names(node: Node) -> set[str]:
    """Collect every identifier name referenced within a subtree."""
    names: set[str] = set()
    _walk_names(node, names)
    return names


def _walk_names(node: Node, out: set[str]) -> None:
    if node.type == "identifier" and node.text is not None:
        out.add(node.text.decode())
    for child in node.children:
        _walk_names(child, out)


def _import_exposes_used_name(node: Node, used: set[str]) -> bool:
    """Return True if any name exposed by this import is in used."""
    if node.type == "import_statement":
        # import a, b as c  →  names: a, c
        for child in node.children:
            if child.type == "dotted_name":
                name = _node_name(child).split(".")[0]
                if name in used:
                    return True
            elif child.type == "aliased_import":
                alias = child.child_by_field_name("alias")
                if alias and _node_name(alias) in used:
                    return True
    elif node.type == "import_from_statement":
        # from x import a, b as c  →  names: a, c
        for child in node.children:
            if child.type == "dotted_name":
                # this might be the module name; skip
                continue
            if child.type == "identifier":
                if _node_name(child) in used:
                    return True
            elif child.type == "aliased_import":
                alias = child.child_by_field_name("alias")
                original = child.child_by_field_name("name")
                exposed = alias or original
                if exposed and _node_name(exposed) in used:
                    return True
    return False


def _get_docstring(node: Node) -> str | None:
    """Extract the docstring from a class or function body node."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    for child in body.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string" and sub.text is not None:
                    raw = sub.text.decode()
                    return raw.strip("\"' \n\r").strip('"""').strip("'''").strip()
    return None


def _is_contract(node: Node) -> bool:
    """Return True if the class looks like a TypedDict, dataclass, or Protocol."""
    superclasses = node.child_by_field_name("superclasses")
    if superclasses:
        for arg in superclasses.children:
            text = _node_name(arg)
            if text in _CONTRACT_BASE_NAMES or text.split(".")[-1] in _CONTRACT_BASE_NAMES:
                return True

    for child in node.children:
        if child.type == "decorator":
            dec_text = _node_name(child).lstrip("@").split("(")[0].split(".")[-1]
            if dec_text == _DATACLASS_DECORATOR:
                return True
    return False
