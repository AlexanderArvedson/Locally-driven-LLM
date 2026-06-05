"""Task types for the Slack-driven scheduler.

Replaces the generic Task/TaskRequest pair with two concrete, self-contained
dataclasses — one per work category. The union type SlackTask is the type
accepted by TaskQueue and TaskDispatcher.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Task dataclasses
# ---------------------------------------------------------------------------


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
    created_at: float = field(default_factory=time.monotonic)


SlackTask = QueryTask | PipelineTask
