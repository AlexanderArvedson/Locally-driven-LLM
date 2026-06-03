"""Maps file extensions to their LanguageSlicer implementation.

To add support for a new language: implement LanguageSlicer, import it here,
and add its file extension to _REGISTRY.
"""

from __future__ import annotations

from pathlib import Path

from src.retrieval.slicing.protocol import LanguageSlicer
from src.retrieval.slicing.python_slicer import PythonSlicer

_REGISTRY: dict[str, type[LanguageSlicer]] = {
    ".py": PythonSlicer,
}


def get_slicer(file_path: str) -> LanguageSlicer | None:
    """Return the slicer for file_path's extension, or None for unsupported languages."""
    suffix = Path(file_path).suffix
    cls = _REGISTRY.get(suffix)
    return cls() if cls is not None else None
