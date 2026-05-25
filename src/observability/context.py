# Context management for graph execution. Provides a RunContext 
# class that holds information about the current execution run, such as a unique run ID.

from dataclasses import dataclass
import uuid

# RunContext holds contextual information for a graph execution run, such as a unique run ID.
@dataclass
class RunContext:
    run_id: str

    @staticmethod
    def new() -> "RunContext":
        return RunContext(run_id=str(uuid.uuid4()))
