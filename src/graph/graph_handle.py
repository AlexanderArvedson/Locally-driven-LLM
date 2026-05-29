from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GraphHandle:
    repo_id: str        # sha256(url + local_path)[:16]
    repo_sha: str       # git HEAD hexsha (40 chars)
    storage_path: Path  # directory containing graph.json
    mode_used: str      # "repo_local" | "system" | "hybrid"
    metadata: dict      # full content of graph_meta.json
