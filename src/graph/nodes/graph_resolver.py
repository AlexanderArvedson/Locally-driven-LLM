"""GraphResolver node — single authority for graph lifecycle.

This node is the ONLY component allowed to read/write graph storage, decide
graph freshness, and trigger graph builds. Downstream nodes receive only a
`GraphHandle` and must not access graph storage directly.

Validity is SHA-based only: a graph is valid when its stored `graph_meta.json`
matches the current git HEAD SHA and the current `GRAPH_SCHEMA_VERSION`.
Timestamps are never used for freshness decisions.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Final

import git
from git.exc import InvalidGitRepositoryError

from src.config_loader import GraphConfig, get_graph_config, get_repository_config, get_system_context_path
from src.graph.graph_handle import GraphHandle
from src.graph.nodes.graphify_indexer import build_ast_graph
from src.graph.state import GraphState
from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_failure, emit_success


GRAPH_SCHEMA_VERSION: Final[int] = 1

_GRAPH_JSON_NAME = "graph.json"
_META_JSON_NAME = "graph_meta.json"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _system_graph_dir(system_root: Path, repo_id: str, repo_sha: str) -> Path:
    """Return the system-store directory for a specific repo and HEAD SHA."""
    return system_root / "graphs" / repo_id / repo_sha


def _repo_local_graph_dir(repo_path: str) -> Path:
    """Return the repo-local ``.graphify/`` directory path."""
    return Path(repo_path) / ".graphify"


# ---------------------------------------------------------------------------
# Identity & git helpers
# ---------------------------------------------------------------------------

def _compute_repo_id(url: str, local_path: str) -> str:
    """Return a 16-char hex identifier stable for a given repo URL and local path.

    Computed as the first 16 characters of sha256(url + local_path), giving a
    collision-resistant directory name that is the same across machines cloning
    the same remote to the same path.
    """
    raw = (url + local_path).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _get_head_sha(repo_path: str) -> str:
    """Return the full 40-char hexsha of the current HEAD commit.

    Raises ``RuntimeError`` if ``repo_path`` is not a valid git repository or
    HEAD cannot be resolved (e.g. empty repo with no commits).
    """
    try:
        repo = git.Repo(repo_path)
        return repo.head.commit.hexsha
    except (InvalidGitRepositoryError, ValueError) as exc:
        raise RuntimeError(f"[graph_resolver] Cannot read HEAD SHA from {repo_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Meta file helpers
# ---------------------------------------------------------------------------

def _read_meta(graph_dir: Path) -> dict | None:
    """Read and parse ``graph_meta.json`` from ``graph_dir``.

    Returns the parsed dict on success, or ``None`` if the file does not exist
    or contains invalid JSON.
    """
    meta_path = graph_dir / _META_JSON_NAME
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_meta(graph_dir: Path, repo_id: str, repo_sha: str) -> dict:
    """Write ``graph_meta.json`` to ``graph_dir`` and return its contents.

    The file records the HEAD SHA, schema version, and repo ID so that future
    calls to ``_is_valid`` can verify freshness without inspecting timestamps.
    ``graph_dir`` must already exist before this is called.
    """
    meta: dict = {
        "repo_sha": repo_sha,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "repo_id": repo_id,
    }
    (graph_dir / _META_JSON_NAME).write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return meta


# ---------------------------------------------------------------------------
# Validity check
# ---------------------------------------------------------------------------

def _is_valid(graph_dir: Path, repo_sha: str) -> tuple[bool, dict | None]:
    """Check whether the graph at ``graph_dir`` is valid for ``repo_sha``.

    A graph is valid only when all of the following hold:
    - ``graph.json`` exists in ``graph_dir``
    - ``graph_meta.json`` exists and is well-formed
    - ``meta["repo_sha"]`` matches ``repo_sha``
    - ``meta["schema_version"]`` matches ``GRAPH_SCHEMA_VERSION``

    Returns a ``(True, meta)`` tuple on success, or ``(False, None)`` if any
    condition fails. Timestamps are never consulted.
    """
    if not (graph_dir / _GRAPH_JSON_NAME).exists():
        return False, None
    meta = _read_meta(graph_dir)
    if meta is None:
        return False, None
    if meta.get("repo_sha") != repo_sha:
        return False, None
    if meta.get("schema_version") != GRAPH_SCHEMA_VERSION:
        return False, None
    return True, meta


# ---------------------------------------------------------------------------
# Graph build
# ---------------------------------------------------------------------------

def _build_graph(repo_path: str, graph_dir: Path, repo_id: str, repo_sha: str) -> dict:
    """Run a full AST extraction for ``repo_path`` and write the graph to ``graph_dir``.

    Creates ``graph_dir`` (and any parents) if it does not exist, delegates
    the actual extraction to ``build_ast_graph``, then writes ``graph_meta.json``
    so the result is immediately recognised as valid by ``_is_valid``.
    Returns the written metadata dict.
    """
    graph_dir.mkdir(parents=True, exist_ok=True)
    build_ast_graph(repo_path, graph_dir)
    return _write_meta(graph_dir, repo_id, repo_sha)


# ---------------------------------------------------------------------------
# Core resolver (pure business logic, synchronous)
# ---------------------------------------------------------------------------

def _resolve_graph_handle(
    repo_path: str,
    repo_id: str,
    repo_sha: str,
    graph_config: GraphConfig,
    system_root: Path,
) -> GraphHandle:
    """Resolve and return a valid ``GraphHandle`` according to the configured mode.

    Implements the three storage strategies:

    - ``repo_local``: checks ``.graphify/`` inside the repo; raises if no valid
      graph is found (never builds automatically).
    - ``system``: checks the system store keyed by ``repo_id/repo_sha``; builds
      if missing or stale, provided ``auto_update`` is ``True``.
    - ``hybrid``: prefers repo-local, falls back to system, then builds into the
      system store when neither is valid and ``auto_update`` is ``True``.

    Raises ``RuntimeError`` when no valid graph is found and building is not
    permitted (``auto_update=False`` or ``repo_local`` mode).
    Raises ``ValueError`` for an unrecognised mode string.
    """
    mode = graph_config.mode
    auto_update = graph_config.auto_update

    if mode == "repo_local":
        graph_dir = _repo_local_graph_dir(repo_path)
        valid, meta = _is_valid(graph_dir, repo_sha)
        if not valid:
            raise RuntimeError(
                f"[graph_resolver] repo_local graph missing or invalid at {graph_dir}. "
                f"Expected SHA={repo_sha[:8]}, schema_version={GRAPH_SCHEMA_VERSION}. "
                "Run graphify manually in the repo or switch to mode='hybrid'."
            )
        return GraphHandle(
            repo_id=repo_id,
            repo_sha=repo_sha,
            storage_path=graph_dir,
            mode_used="repo_local",
            metadata=meta,
        )

    if mode == "system":
        graph_dir = _system_graph_dir(system_root, repo_id, repo_sha)
        valid, meta = _is_valid(graph_dir, repo_sha)
        if valid:
            return GraphHandle(
                repo_id=repo_id,
                repo_sha=repo_sha,
                storage_path=graph_dir,
                mode_used="system",
                metadata=meta,
            )
        if not auto_update:
            raise RuntimeError(
                f"[graph_resolver] system graph missing or invalid for "
                f"repo_id={repo_id}, sha={repo_sha[:8]} and auto_update=False."
            )
        meta = _build_graph(repo_path, graph_dir, repo_id, repo_sha)
        return GraphHandle(
            repo_id=repo_id,
            repo_sha=repo_sha,
            storage_path=graph_dir,
            mode_used="system",
            metadata=meta,
        )

    if mode == "hybrid":
        # 1. Try repo_local
        local_dir = _repo_local_graph_dir(repo_path)
        valid, meta = _is_valid(local_dir, repo_sha)
        if valid:
            return GraphHandle(
                repo_id=repo_id,
                repo_sha=repo_sha,
                storage_path=local_dir,
                mode_used="repo_local",
                metadata=meta,
            )
        # 2. Try system
        sys_dir = _system_graph_dir(system_root, repo_id, repo_sha)
        valid, meta = _is_valid(sys_dir, repo_sha)
        if valid:
            return GraphHandle(
                repo_id=repo_id,
                repo_sha=repo_sha,
                storage_path=sys_dir,
                mode_used="system",
                metadata=meta,
            )
        # 3. Build into system storage
        if not auto_update:
            raise RuntimeError(
                f"[graph_resolver] No valid graph found in hybrid mode for "
                f"repo_id={repo_id}, sha={repo_sha[:8]} and auto_update=False."
            )
        meta = _build_graph(repo_path, sys_dir, repo_id, repo_sha)
        return GraphHandle(
            repo_id=repo_id,
            repo_sha=repo_sha,
            storage_path=sys_dir,
            mode_used="system",
            metadata=meta,
        )

    raise ValueError(f"[graph_resolver] Unknown graph mode: {mode!r}")


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

async def graph_resolver_node(state: GraphState, run_context: RunContext) -> dict:
    """Resolve a valid knowledge graph for the target repository.

    Determines the correct graph storage path based on mode and SHA validity,
    building the graph only when necessary. Returns a GraphHandle for
    downstream nodes; sets graph_path for context_builder compatibility.
    """
    start = time.time()
    try:
        repo_path = state.get("repo_path")
        if not repo_path:
            emit_success(
                run_context, "graph_resolver_node",
                {"skipped": True, "reason": "no repo_path"},
                start,
            )
            return {}

        repo_config = get_repository_config(repo_path)
        graph_config = get_graph_config(repo_path)
        repo_id = _compute_repo_id(repo_config.url, repo_config.local_path)
        repo_sha = _get_head_sha(repo_path)
        system_root = get_system_context_path()

        handle = _resolve_graph_handle(
            repo_path=repo_path,
            repo_id=repo_id,
            repo_sha=repo_sha,
            graph_config=graph_config,
            system_root=system_root,
        )

        emit_success(
            run_context, "graph_resolver_node",
            {
                "mode_used": handle.mode_used,
                "repo_id": handle.repo_id,
                "repo_sha": handle.repo_sha[:8],
                "storage_path": str(handle.storage_path),
            },
            start,
        )
        # graph_handle is internal to this node; downstream nodes receive only
        # lightweight references (graph_path + repo_sha) so state stays lean.
        return {
            "graph_path": str(handle.storage_path),
            "repo_sha": repo_sha,
            "graph_snapshot_sha": repo_sha,
        }
    except Exception as exc:
        emit_failure(run_context, "graph_resolver_node", str(exc), start)
        raise
