from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from .task import Task


class WorkflowExecutor:
    """Executor that runs a workflow graph for a given `Task`.

    The executor accepts optional `graph_factory` and `run_context_factory`
    callables to allow dependency injection for testing. The core
    implementation performs a local import of `make_graph` to avoid import
    cycles when the scheduler is used from higher-level code.
    """

    def __init__(self, graph_factory=None, run_context_factory=None) -> None:
        self._graph_factory = graph_factory
        self._run_context_factory = run_context_factory

    async def execute(self, task: Task):
        from src.graph.workflow import make_graph
        from src.graph.state import GraphState
        from src.observability.context import RunContext
        from src.observability.logger import write_run_summary, format_run_console
        from src.config_loader import get_repository_config, update_repository_timestamps

        graph_factory = self._graph_factory or make_graph
        run_context_factory = self._run_context_factory or RunContext.new

        run_context = run_context_factory()
        state = cast(GraphState, task.payload)

        # Stamp task on run_context so it appears once in the top-level run summary
        run_context.task = state.get("task", "")

        graph = graph_factory(run_context)

        repo_path = state.get("repo_path")
        if repo_path:
            try:
                repo_config = get_repository_config(repo_path)
                if not repo_config.created_at:
                    update_repository_timestamps(
                        repo_config.name,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
            except Exception:
                pass

        final_status = "success"
        try:
            result = await graph.ainvoke(state)
        except Exception:
            final_status = "failure"
            raise
        finally:
            write_run_summary(run_context, final_status)
            print(format_run_console(run_context, final_status))

        return result
