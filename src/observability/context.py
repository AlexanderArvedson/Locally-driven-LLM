"""RunContext helper for observability.

This module provides a minimal `RunContext` dataclass which carries per-run
observability information outside of the business `GraphState`. In addition to
a unique `run_id`, it holds the task description, the wall-clock start time, and
an in-memory list of emitted events that is used to produce the aggregated run
summary at the end of execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid


@dataclass
class RunContext:
    """Per-run observability context.

    Attributes:
        run_id: A UUID4 string uniquely identifying this execution run.
        task: The task description sourced from GraphState before graph invocation.
        started_at: ISO 8601 UTC timestamp of when the run was created.
        events: Accumulated compact event dicts, one per node execution.
    """
    run_id: str
    task: str = ""
    started_at: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def new() -> "RunContext":
        """Create a fresh RunContext with a new UUID4 run_id and current timestamp."""
        return RunContext(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
        )
