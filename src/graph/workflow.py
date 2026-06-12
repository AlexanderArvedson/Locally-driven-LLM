"""Graph construction helpers for the file-edit workflow.

This module builds a `StateGraph` for the file-edit workflow and provides a
factory `make_graph(run_context)` that returns a compiled graph wired so each
node receives the provided `RunContext` instance.

Observability is intentionally separated from `GraphState`; the graph factory
binds the runtime `run_context` into node callables using a small wrapper so
the graph runtime can continue to invoke nodes with the single-argument
signature it expects.
"""

from langgraph.graph import StateGraph, START, END

from src.graph.state import GraphState
from src.graph.nodes import node_index as nodes_module
from src.core.config_loader import get_max_workflow_revision_cycles
from src.observability.context import RunContext



def route_after_review(state: GraphState):
    """Decide the next graph node after the `reviewer` (static_validator) node.

    - If the review passed, continue to the `semantic_validator` node.
    - If the iteration limit was reached, end the run.
    - Otherwise, route back to `coder` for another iteration.

    The function signature matches what `StateGraph.add_conditional_edges`
    expects: it receives the current `state` and returns the next node key or
    `END`.
    """
    if state.get("review_passed"):
        return "semantic_validator"
    if state.get("iteration", 0) >= get_max_workflow_revision_cycles(state.get("repo_path")):
        return END
    return "coder"


def route_after_semantic(state: GraphState):
    """Decide the next graph node after the `semantic_validator` node.

    - If semantic validation passed (score >= threshold), proceed to file_writer.
    - If the iteration limit was reached, end the run.
    - Otherwise, route back to `coder` with structured misalignment feedback.
    """
    if state.get("semantic_passed"):
        return "file_writer"
    if state.get("iteration", 0) >= get_max_workflow_revision_cycles(state.get("repo_path")):
        return END
    return "coder"


def route_after_planner(state: GraphState):
    """Terminate early when the planner found no file to modify."""
    if state.get("planner_error"):
        return END
    return "file_reader"


def make_graph(run_context: RunContext):
    """Create and compile the StateGraph for a single run.

    The returned graph is compiled with every node wrapped so it receives the
    provided `run_context` as a second argument. This keeps `GraphState`
    unchanged while enabling per-run observability via `RunContext`.

    Args:
        run_context: the RunContext instance to bind into node callables.

    Returns:
        A compiled `StateGraph` instance ready for invocation.
    """
    builder = StateGraph(GraphState)

    # Helper to convert node implementations of the form
    #     async def node(state, run_context): ...
    # into callables that the graph runtime can call with a single `state`
    # argument. The wrapper binds `run_context` into the closure.
    def _wrap(node_func):
        async def _wrapped(state):
            return await node_func(state, run_context)

        return _wrapped

    # Register nodes from the aggregate index module.
    builder.add_node("branch_creator", _wrap(nodes_module.branch_creator_node))
    builder.add_node("graph_resolver", _wrap(nodes_module.graph_resolver_node))
    builder.add_node("retrieval", _wrap(nodes_module.retrieval_node))
    builder.add_node("planner", _wrap(nodes_module.planner_node))
    builder.add_node("file_reader", _wrap(nodes_module.file_reader_node))
    builder.add_node("coder", _wrap(nodes_module.coder_node))
    builder.add_node("diff_generator", _wrap(nodes_module.diff_generator_node))
    builder.add_node("reviewer", _wrap(nodes_module.static_validator_node))
    builder.add_node("semantic_validator", _wrap(nodes_module.semantic_validator_node))
    builder.add_node("file_writer", _wrap(nodes_module.file_writer_node))
    builder.add_node("git_committer", _wrap(nodes_module.git_committer_node))

    # Pipeline:
    #   branch_creator → graph_resolver → retrieval → planner → file_reader → coder → ...
    # planner selects target_file from retrieval candidates; terminates early on error.
    builder.add_edge(START, "branch_creator")
    builder.add_edge("branch_creator", "graph_resolver")
    builder.add_edge("graph_resolver", "retrieval")
    builder.add_edge("retrieval", "planner")
    builder.add_edge("file_reader", "coder")
    builder.add_edge("coder", "diff_generator")
    builder.add_edge("diff_generator", "reviewer")
    builder.add_edge("file_writer", "git_committer")
    builder.add_edge("git_committer", END)

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "file_reader": "file_reader",
            END: END,
        },
    )

    builder.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "coder": "coder",
            "semantic_validator": "semantic_validator",
            END: END,
        },
    )

    builder.add_conditional_edges(
        "semantic_validator",
        route_after_semantic,
        {
            "coder": "coder",
            "file_writer": "file_writer",
            END: END,
        },
    )

    return builder.compile()
