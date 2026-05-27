from __future__ import annotations

from typing import cast

from .task import Task


class WorkflowExecutor:
    def __init__(self, graph_factory=None, run_context_factory=None) -> None:
        self._graph_factory = graph_factory
        self._run_context_factory = run_context_factory

    async def execute(self, task: Task):
        from src.graph.workflow import make_graph
        from src.graph.state import GraphState
        from src.observability.context import RunContext

        graph_factory = self._graph_factory or make_graph
        run_context_factory = self._run_context_factory or RunContext.new
        graph = graph_factory(run_context_factory())
        state = cast(GraphState, task.payload)
        return await graph.ainvoke(state)
