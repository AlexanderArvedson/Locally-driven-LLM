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
    return system_root / "graphs" / repo_id / repo_sha


def _repo_local_graph_dir(repo_path: str) -> Path:
    return Path(repo_path) / ".graphify"


# ---------------------------------------------------------------------------
# Identity & git helpers
# ---------------------------------------------------------------------------

def _compute_repo_id(url: str, local_path: str) -> str:
    raw = (url + local_path).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _get_head_sha(repo_path: str) -> str:
    try:
        repo = git.Repo(repo_path)
        return repo.head.commit.hexsha
    except (InvalidGitRepositoryError, ValueError) as exc:
        raise RuntimeError(f"[graph_resolver] Cannot read HEAD SHA from {repo_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Meta file helpers
# ---------------------------------------------------------------------------

def _read_meta(graph_dir: Path) -> dict | None:
    meta_path = graph_dir / _META_JSON_NAME
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_meta(graph_dir: Path, repo_id: str, repo_sha: str) -> dict:
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
    task = state.get("task", "")
    try:
        repo_path = state.get("repo_path")
        if not repo_path:
            emit_success(
                run_context, "graph_resolver_node", task,
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
            run_context, "graph_resolver_node", task,
            {
                "mode_used": handle.mode_used,
                "repo_id": handle.repo_id,
                "repo_sha": handle.repo_sha[:8],
                "storage_path": str(handle.storage_path),
            },
            start,
        )
        return {
            "graph_handle": handle,
            "graph_path": str(handle.storage_path),
            "repo_sha": repo_sha,
        }
    except Exception as exc:
        emit_failure(run_context, "graph_resolver_node", task, str(exc), start)
        raise
