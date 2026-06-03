"""Symbol-level context slicing for language-agnostic code extraction."""

from src.retrieval.slicing.protocol import LanguageSlicer, SymbolSlice
from src.retrieval.slicing.registry import get_slicer

__all__ = ["LanguageSlicer", "SymbolSlice", "get_slicer"]
