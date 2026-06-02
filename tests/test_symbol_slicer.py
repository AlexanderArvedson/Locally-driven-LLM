"""Tests for the symbol-level slicing module."""

import pytest

from src.retrieval.slicing import SymbolSlice, get_slicer
from src.retrieval.slicing.python_slicer import PythonSlicer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MODULE_SOURCE = '''\
import os
import sys
from typing import TypedDict


class Config(TypedDict):
    value: int


def simple(x: int) -> int:
    return x + 1


async def async_fn(cfg: Config) -> str:
    return os.path.join(str(cfg["value"]))


class Processor:
    """Handles processing."""

    def run(self, value: int) -> int:
        return value * 2

    def helper(self) -> None:
        sys.exit(0)
'''


@pytest.fixture()
def slicer() -> PythonSlicer:
    return PythonSlicer()


# ---------------------------------------------------------------------------
# extract_symbol
# ---------------------------------------------------------------------------

class TestExtractSymbol:
    def test_module_level_function(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "simple")
        assert sl is not None
        assert sl.name == "simple"
        assert "def simple" in sl.source
        assert sl.indent == 0

    def test_async_function(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "async_fn")
        assert sl is not None
        assert "async def async_fn" in sl.source

    def test_class(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "Processor")
        assert sl is not None
        assert "class Processor" in sl.source
        assert "def run" in sl.source

    def test_method(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "run")
        assert sl is not None
        assert "def run" in sl.source
        assert sl.indent == 4

    def test_unknown_name_returns_none(self, slicer: PythonSlicer) -> None:
        assert slicer.extract_symbol(_MODULE_SOURCE, "nonexistent") is None

    def test_bad_syntax_returns_none(self, slicer: PythonSlicer) -> None:
        assert slicer.extract_symbol("def (", "foo") is None

    def test_start_end_lines_are_correct(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "simple")
        assert sl is not None
        lines = _MODULE_SOURCE.splitlines()
        assert lines[sl.start_line - 1].startswith("def simple")
        assert lines[sl.end_line - 1].strip() == "return x + 1"


# ---------------------------------------------------------------------------
# stitch_symbol
# ---------------------------------------------------------------------------

class TestStitchSymbol:
    def test_replaces_function_body(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "simple")
        assert sl is not None
        modified = "def simple(x: int) -> int:\n    return x * 2\n"
        result = slicer.stitch_symbol(_MODULE_SOURCE, sl, modified)
        assert "return x * 2" in result
        assert "return x + 1" not in result
        # Surrounding code must be preserved.
        assert "import os" in result
        assert "class Processor" in result

    def test_reapplies_missing_indent_for_method(self, slicer: PythonSlicer) -> None:
        sl = slicer.extract_symbol(_MODULE_SOURCE, "run")
        assert sl is not None
        assert sl.indent == 4
        # LLM strips the leading 4 spaces.
        modified = "def run(self, value: int) -> int:\n    return value * 3\n"
        result = slicer.stitch_symbol(_MODULE_SOURCE, sl, modified)
        assert "    def run" in result
        assert "return value * 3" in result

    def test_unchanged_when_symbol_missing(self, slicer: PythonSlicer) -> None:
        phantom = SymbolSlice(name="ghost", source="def ghost(): pass\n", start_line=999, end_line=999, indent=0)
        result = slicer.stitch_symbol(_MODULE_SOURCE, phantom, "def ghost(): pass\n")
        assert result == _MODULE_SOURCE


# ---------------------------------------------------------------------------
# extract_imports_for
# ---------------------------------------------------------------------------

class TestExtractImportsFor:
    def test_returns_only_used_imports(self, slicer: PythonSlicer) -> None:
        imports = slicer.extract_imports_for(_MODULE_SOURCE, "async_fn")
        assert "import os" in imports
        assert "import sys" not in imports

    def test_method_uses_sys(self, slicer: PythonSlicer) -> None:
        imports = slicer.extract_imports_for(_MODULE_SOURCE, "helper")
        assert "import sys" in imports
        assert "import os" not in imports

    def test_empty_for_unknown_symbol(self, slicer: PythonSlicer) -> None:
        assert slicer.extract_imports_for(_MODULE_SOURCE, "nope") == ""


# ---------------------------------------------------------------------------
# extract_class_context
# ---------------------------------------------------------------------------

class TestExtractClassContext:
    def test_method_returns_class_header(self, slicer: PythonSlicer) -> None:
        ctx = slicer.extract_class_context(_MODULE_SOURCE, "run")
        assert ctx is not None
        assert "class Processor" in ctx

    def test_includes_docstring_summary(self, slicer: PythonSlicer) -> None:
        ctx = slicer.extract_class_context(_MODULE_SOURCE, "run")
        assert ctx is not None
        assert "Handles processing" in ctx

    def test_module_level_function_returns_none(self, slicer: PythonSlicer) -> None:
        assert slicer.extract_class_context(_MODULE_SOURCE, "simple") is None


# ---------------------------------------------------------------------------
# extract_contracts
# ---------------------------------------------------------------------------

class TestExtractContracts:
    def test_typed_dict_is_extracted(self, slicer: PythonSlicer) -> None:
        contracts = slicer.extract_contracts(_MODULE_SOURCE, "async_fn")
        assert "class Config(TypedDict)" in contracts

    def test_no_contracts_for_unrelated_symbol(self, slicer: PythonSlicer) -> None:
        contracts = slicer.extract_contracts(_MODULE_SOURCE, "simple")
        assert contracts == ""


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_python_extension_returns_slicer(self) -> None:
        s = get_slicer("src/foo.py")
        assert isinstance(s, PythonSlicer)

    def test_unsupported_extension_returns_none(self) -> None:
        assert get_slicer("src/foo.go") is None
        assert get_slicer("src/foo.ts") is None
        assert get_slicer("src/foo") is None
