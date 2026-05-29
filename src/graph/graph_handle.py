from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GraphHandle:
    """Immutable reference to a resolved, validated knowledge graph.

    Produced exclusively by `graph_resolver_node` and passed to downstream
    nodes. No component other than the resolver may read or write the
    underlying graph storage.

    Attributes:
        repo_id: 16-char hex derived from sha256(url + local_path).
        repo_sha: Full 40-char git HEAD hexsha at the time of resolution.
        storage_path: Directory that contains ``graph.json`` and
            ``graph_meta.json`` for this graph version.
        mode_used: Storage mode that produced this handle —
            ``"repo_local"``, ``"system"``, or ``"hybrid"``.
        metadata: Parsed content of ``graph_meta.json`` as written by the
            resolver (includes ``repo_sha``, ``schema_version``, ``repo_id``).
    """

    repo_id: str        # sha256(url + local_path)[:16]
    repo_sha: str       # git HEAD hexsha (40 chars)
    storage_path: Path  # directory containing graph.json
    mode_used: str      # "repo_local" | "system" | "hybrid"
    metadata: dict      # full content of graph_meta.json
