"""RunContext helper for observability.

This module provides a minimal `RunContext` dataclass which currently only
contains a UUID4 `run_id`. The intent is to carry per-run observability
information outside of the business `GraphState`.
"""

from dataclasses import dataclass
import uuid


@dataclass
class RunContext:
    """Minimal per-run observability context.

    Attributes:
        run_id: A UUID4 string uniquely identifying this execution run.
    """
    run_id: str

    @staticmethod
    def new() -> "RunContext":
        """Create a fresh RunContext with a new UUID4 run_id."""
        return RunContext(run_id=str(uuid.uuid4()))
