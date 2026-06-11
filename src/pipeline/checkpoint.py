"""Mid-run checkpoint persistence for the pipeline.

Saves expensive per-record fields (descriptions and embeddings) to disk so a
crashed run can resume from the last saved point instead of restarting from
scratch.  The checkpoint is keyed by a hash of the changed-record IDs, so it
is automatically considered stale if the changed set shifts between runs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipeline.contracts import CheckpointConfig, FunctionRecord

logger = logging.getLogger(__name__)

_SAVED_FIELDS = (
    "description",
    "description_status",
    "code_embedding",
    "code_embedding_status",
    "description_embedding",
)


def make_run_key(records: list[FunctionRecord]) -> str:
    """Derive a stable key for this set of changed records.

    The key is the first 12 hex chars of sha256(sorted record IDs), which
    becomes stale automatically when the changed-set shifts (e.g. new commits).
    """
    digest = hashlib.sha256(
        ",".join(sorted(r.id for r in records)).encode()
    ).hexdigest()
    return digest[:12]


class CheckpointManager:
    """Persists and restores mid-run pipeline state to a local JSON file."""

    def __init__(self, config: CheckpointConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, repo_name: str, run_key: str) -> dict[str, dict]:
        """Return saved record fields keyed by record ID, or {} if missing/stale/corrupt."""
        if not self._config.enabled:
            return {}
        path = self._checkpoint_path(repo_name, run_key)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            if data.get("run_key") != run_key:
                logger.debug("Checkpoint run_key mismatch — ignoring stale file %s", path)
                return {}
            records: dict[str, dict] = data.get("records", {})
            logger.info("Loaded checkpoint with %d records from %s", len(records), path)
            return records
        except Exception:
            logger.warning("Checkpoint file %s is corrupt or unreadable — ignoring", path)
            return {}

    def save(self, repo_name: str, run_key: str, records: list[FunctionRecord]) -> None:
        """Atomically write the expensive fields of all records to disk."""
        if not self._config.enabled:
            return
        directory = Path(self._config.directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = self._checkpoint_path(repo_name, run_key)
        tmp = path.with_suffix(".tmp")
        payload = {
            "run_key": run_key,
            "records": {
                r.id: {field: getattr(r, field) for field in _SAVED_FIELDS}
                for r in records
            },
        }
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, path)  # atomic on POSIX; survives a crash mid-write
        logger.debug("Checkpoint saved (%d records) → %s", len(records), path)

    def clear(self, repo_name: str, run_key: str) -> None:
        """Delete the checkpoint file after a successful pipeline run."""
        if not self._config.enabled:
            return
        path = self._checkpoint_path(repo_name, run_key)
        if path.exists():
            path.unlink()
            logger.debug("Checkpoint cleared: %s", path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _checkpoint_path(self, repo_name: str, run_key: str) -> Path:
        safe_name = repo_name.replace(" ", "_").replace("/", "_")
        return Path(self._config.directory) / f"{safe_name}_{run_key}.json"
