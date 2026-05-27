"""SQLite-backed execution registry for Phase 3 lifecycle persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.core.runtime_paths import RUNTIME_DIR, ensure_runtime_dirs
from src.runtime.models import (
    ExecutionRequest,
    ExecutionResult,
    RunStatus,
    WorkflowCapability,
    WorkflowMode,
    isoformat_utc,
    utc_now,
)


ACTIVE_STATUSES = {RunStatus.QUEUED.value, RunStatus.RUNNING.value}


@dataclass(slots=True)
class RunRecord:
    """Persisted lifecycle record for one execution run."""

    run_id: str
    workflow_mode: WorkflowMode
    workflow_capability: WorkflowCapability
    trigger: str
    repository_path: Path
    repository_revision: str
    status: RunStatus
    created_at: datetime
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None
    error: str | None = None
    payload: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    artifacts: dict[str, Any] | None = None
    result_metadata: dict[str, Any] | None = None


def _dump_json(value: dict[str, Any] | None) -> str:
    """Serialize a dictionary as a JSON string, treating None as an empty object for convenience."""
    return json.dumps(value or {}, sort_keys=True)


def _load_json(value: str | None) -> dict[str, Any] | None:
    """Deserialize a JSON string into a dictionary, treating None as None."""
    if value is None:
        return None
    return json.loads(value)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime string into a timezone-aware datetime object, 
    treating None as None."""
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class RunRegistry:
    """SQLite-backed system of record for execution lifecycle state."""

    def __init__(self, db_path: Path | None = None):
        """Initialize the registry, creating the database file and schema if needed."""
        ensure_runtime_dirs()
        self.db_path = db_path or (RUNTIME_DIR / "scheduler.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        """Create a new connection to the SQLite database with appropriate settings."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        """Create the runs table if it doesn't already exist."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    workflow_mode TEXT NOT NULL,
                    workflow_capability TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    repository_path TEXT NOT NULL,
                    repository_revision TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    queued_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    error TEXT,
                    payload_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    artifacts_json TEXT NOT NULL,
                    result_metadata_json TEXT NOT NULL
                )
                """
            )

    def create_run(self, request: ExecutionRequest, status: RunStatus = RunStatus.PENDING) -> RunRecord:
        """Create a new run record from an execution request, returning the created record."""
        now = utc_now()
        record = RunRecord(
            run_id=request.run_id,
            workflow_mode=request.workflow_mode,
            workflow_capability=request.workflow_capability,
            trigger=request.trigger,
            repository_path=request.repository_path,
            repository_revision=request.repository_revision,
            status=status,
            created_at=request.created_at,
            updated_at=now,
            payload=request.payload,
            metadata=request.metadata,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    run_id,
                    workflow_mode,
                    workflow_capability,
                    trigger,
                    repository_path,
                    repository_revision,
                    status,
                    created_at,
                    queued_at,
                    started_at,
                    completed_at,
                    updated_at,
                    error,
                    payload_json,
                    metadata_json,
                    artifacts_json,
                    result_metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.workflow_mode.value,
                    record.workflow_capability.value,
                    record.trigger,
                    str(record.repository_path),
                    record.repository_revision,
                    record.status.value,
                    isoformat_utc(record.created_at),
                    None,
                    None,
                    None,
                    isoformat_utc(record.updated_at),
                    None,
                    _dump_json(record.payload),
                    _dump_json(record.metadata),
                    _dump_json(record.artifacts),
                    _dump_json(record.result_metadata),
                ),
            )
        return record

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        queued_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
        artifacts: dict[str, Any] | None = None,
        result_metadata: dict[str, Any] | None = None,
    ) -> RunRecord:
        """Update the status and timestamps of an existing run record, returning the updated record."""
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = ?, queued_at = COALESCE(?, queued_at), started_at = COALESCE(?, started_at),
                    completed_at = COALESCE(?, completed_at), updated_at = ?, error = COALESCE(?, error),
                    artifacts_json = COALESCE(?, artifacts_json), result_metadata_json = COALESCE(?, result_metadata_json)
                WHERE run_id = ?
                """,
                (
                    status.value,
                    isoformat_utc(queued_at) if queued_at else None,
                    isoformat_utc(started_at) if started_at else None,
                    isoformat_utc(completed_at) if completed_at else None,
                    isoformat_utc(now),
                    error,
                    _dump_json(artifacts) if artifacts is not None else None,
                    _dump_json(result_metadata) if result_metadata is not None else None,
                    run_id,
                ),
            )
        record = self.get_run(run_id)
        if record is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        return record

    def record_failure(self, run_id: str, error: str) -> RunRecord:
        """Mark a run as failed with the given error message, returning the updated record."""
        return self.update_status(run_id, RunStatus.FAILED, completed_at=utc_now(), error=error)

    def record_result(self, result: ExecutionResult) -> RunRecord:
        """Record the result of a completed execution, marking it as completed or failed based on success."""
        return self.update_status(
            result.run_id,
            RunStatus.COMPLETED if result.success else RunStatus.FAILED,
            started_at=result.started_at,
            completed_at=result.completed_at,
            error=result.error,
            artifacts=result.artifacts,
            result_metadata=result.metadata,
        )

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_active_runs(self) -> list[RunRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs WHERE status IN (?, ?) ORDER BY created_at ASC, run_id ASC",
                tuple(ACTIVE_STATUSES),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def find_stale_runs(self, timeout_seconds: int) -> list[RunRecord]:
        cutoff = utc_now() - timedelta(seconds=timeout_seconds)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs WHERE status = ? AND started_at IS NOT NULL",
                (RunStatus.RUNNING.value,),
            ).fetchall()
        stale_runs = []
        for row in rows:
            record = self._row_to_record(row)
            if record.started_at is not None and record.started_at < cutoff:
                stale_runs.append(record)
        return stale_runs

    def _row_to_record(self, row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            workflow_mode=WorkflowMode(row["workflow_mode"]),
            workflow_capability=WorkflowCapability(row["workflow_capability"]),
            trigger=row["trigger"],
            repository_path=Path(row["repository_path"]),
            repository_revision=row["repository_revision"],
            status=RunStatus(row["status"]),
            created_at=_parse_datetime(row["created_at"]) or utc_now(),
            queued_at=_parse_datetime(row["queued_at"]),
            started_at=_parse_datetime(row["started_at"]),
            completed_at=_parse_datetime(row["completed_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
            error=row["error"],
            payload=_load_json(row["payload_json"]),
            metadata=_load_json(row["metadata_json"]),
            artifacts=_load_json(row["artifacts_json"]),
            result_metadata=_load_json(row["result_metadata_json"]),
        )
