"""Task types for the scheduler.

Two concrete work units and their union — the type accepted by TaskQueue,
ExecutionLoop, and TaskDispatcher.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class QueryTask:
    """A semantic search request — passive (never holds the mutation lock)."""

    id: str
    query_text: str
    response_url: str
    repo: str
    type: Literal["passive"] = "passive"
    top_n: int = 10
    created_at: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class PipelineTask:
    """A full embedding-pipeline run — active (serialised behind the mutation lock)."""

    id: str
    repo: str
    type: Literal["active"] = "active"
    no_descriptions: bool = False
    dry_run: bool = False
    no_report: bool = False
    path: str | None = None
    created_at: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class ReportTask:
    """A report-generation run — active (serialised behind the mutation lock)."""

    id: str
    repo: str
    loc_filtered: int = 0
    type: Literal["active"] = "active"
    created_at: float = field(default_factory=time.monotonic)


Task = QueryTask | PipelineTask | ReportTask
