"""Language-agnostic slicing Protocol.

Defines the shared contract that every language-specific slicer must satisfy.
Adding support for a new language means implementing ``LanguageSlicer`` and
registering the file extension in ``registry.py`` — no other changes required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class SymbolSlice:
    """Everything extracted about one symbol from a source file."""

    name: str
    source: str      # verbatim source including decorators, original indentation
    start_line: int  # 1-based, includes decorators if any
    end_line: int    # 1-based, inclusive
    indent: int      # number of leading spaces on the first line


@runtime_checkable
class LanguageSlicer(Protocol):
    """Extract and stitch back a named symbol within a source file."""

    def extract_symbol(self, source: str, name: str) -> SymbolSlice | None:
        """Return a SymbolSlice for the named function/class, or None if not found."""
        ...

    def extract_imports_for(self, source: str, symbol_name: str) -> str:
        """Return import lines that are actually referenced by the named symbol."""
        ...

    def extract_class_context(self, source: str, method_name: str) -> str | None:
        """If method_name is a method, return its enclosing class header + docstring."""
        ...

    def extract_contracts(self, source: str, symbol_name: str) -> str:
        """Return type-contract class definitions (TypedDict/dataclass/Protocol) used by the symbol."""
        ...

    def stitch_symbol(self, original: str, sl: SymbolSlice, modified: str) -> str:
        """Replace the original symbol with the modified version and return the full file."""
        ...
