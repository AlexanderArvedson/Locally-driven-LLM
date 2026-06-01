"""Versioned contract for retrieval -> coder repository context payloads.

This module is the single source of truth for the context shape, ordering
rules, and prompt rendering used at the retrieval/coder boundary.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Mapping, TypedDict

from src.retrieval.contracts.types import ContextPackage


CONTEXT_VERSION = 1

REQUIRED_CONTEXT_FIELDS = (
    "context_version",
    "primary_file",
    "selected_files",
    "related_files",
    "related_symbols",
    "dependency_summary",
    "total_symbols",
)


class DependencySummaryItem(TypedDict):
    from_path: str
    to_path: str
    import_text: str | None


class RepositoryContextPayload(TypedDict):
    context_version: int
    primary_file: str | None
    selected_files: list[str]
    related_files: list[str]
    related_symbols: dict[str, list[str]]
    dependency_summary: list[DependencySummaryItem]
    total_symbols: int


def _normalize_path(path: str, repo_path: str | None) -> str:
    if not repo_path:
        return path
    try:
        return os.path.relpath(path, repo_path).replace(os.sep, "/")
    except Exception:
        return path


def _dedupe_preserve_order(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def _target_first(selected_files: list[str], target_file: str | None) -> list[str]:
    selected = _dedupe_preserve_order(selected_files)
    if target_file and target_file in selected:
        return [target_file] + [path for path in selected if path != target_file]
    return selected


def build_repository_context_payload(
    context_package: ContextPackage,
    selected_files: list[str],
    *,
    repo_path: str | None = None,
) -> RepositoryContextPayload:
    """Build a versioned, deterministic context payload from ContextPackage."""
    primary = _normalize_path(context_package.primary_file, repo_path) if context_package.primary_file else None

    normalized_selected = [_normalize_path(path, repo_path) for path in selected_files]
    normalized_selected = _target_first(normalized_selected, primary)

    normalized_related = [_normalize_path(path, repo_path) for path in context_package.related_files]
    normalized_related = _target_first(normalized_related, primary)

    related_symbols: dict[str, list[str]] = {}
    for path in sorted(context_package.related_symbols):
        normalized = _normalize_path(path, repo_path)
        related_symbols[normalized] = list(context_package.related_symbols[path])

    dependency_summary: list[DependencySummaryItem] = []
    for edge in context_package.dependency_summary:
        dependency_summary.append(
            {
                "from_path": _normalize_path(edge.from_path, repo_path),
                "to_path": _normalize_path(edge.to_path, repo_path),
                "import_text": edge.import_text,
            }
        )

    dependency_summary = sorted(
        dependency_summary,
        key=lambda item: (item["from_path"], item["to_path"], item.get("import_text") or ""),
    )

    return {
        "context_version": CONTEXT_VERSION,
        "primary_file": primary,
        "selected_files": normalized_selected,
        "related_files": normalized_related,
        "related_symbols": related_symbols,
        "dependency_summary": dependency_summary,
        "total_symbols": int(context_package.total_symbols),
    }


def validate_repository_context_payload(payload: Mapping[str, Any] | None) -> tuple[bool, str]:
    """Validate structural invariants for a repository context payload."""
    if payload is None:
        return False, "missing payload"

    for key in REQUIRED_CONTEXT_FIELDS:
        if key not in payload:
            return False, f"missing required field: {key}"

    if payload.get("context_version") != CONTEXT_VERSION:
        return False, "invalid context_version"

    selected = payload.get("selected_files")
    if not isinstance(selected, list):
        return False, "selected_files must be a list"

    primary = payload.get("primary_file")
    if primary and selected and selected[0] != primary:
        return False, "primary_file must be first in selected_files"

    return True, "ok"


def format_repository_context_for_prompt(repository_context: Mapping[str, Any] | None) -> str:
    """Render repository context in a fixed, deterministic prompt section."""
    if not repository_context:
        return "[REPOSITORY CONTEXT]\n- none"

    is_valid, _reason = validate_repository_context_payload(repository_context)
    if not is_valid:
        return "[REPOSITORY CONTEXT]\n- invalid"

    lines: list[str] = ["[REPOSITORY CONTEXT]"]
    lines.append(f"- context_version: {repository_context['context_version']}")

    selected_files = repository_context.get("selected_files", [])
    lines.append("- selected_files:")
    for index, path in enumerate(selected_files, start=1):
        lines.append(f"  {index}. {path}")

    related_symbols = repository_context.get("related_symbols", {})
    if related_symbols:
        lines.append("- related_symbols:")
        for path in sorted(related_symbols):
            symbols = related_symbols[path]
            rendered = ", ".join(symbols) if symbols else "<none>"
            lines.append(f"  - {path}: {rendered}")

    lines.append(f"- total_symbols: {repository_context.get('total_symbols', 0)}")
    return "\n".join(lines)
