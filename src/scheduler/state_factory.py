from __future__ import annotations

from src.graph.state import GraphState
from .task_request import TaskRequest


class GraphStateFactory:
    """Converts an external TaskRequest into the internal GraphState.

    This is the single authoritative path from user request to graph state.
    No other code should construct a GraphState dict from raw user input.
    """

    @staticmethod
    def from_task_request(request: TaskRequest) -> GraphState:
        """Build the initial GraphState from a validated TaskRequest."""
        state: GraphState = {
            "task": request.task,
            "repo_path": request.repo_path,
            "task_request": request,
        }
        if request.target_path is not None:
            state["target_file"] = request.target_path
        return state
