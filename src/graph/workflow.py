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
from src.graph.nodes.coder import coder_node
from src.graph.nodes.context_builder import context_builder_node
from src.graph.nodes.diff_generator import diff_generator_node
from src.graph.nodes.file_reader import file_reader_node
from src.graph.nodes.file_writer import file_writer_node
from src.graph.nodes.reviewer import reviewer_node
from src.graph.nodes.verifier import verifier_node
from src.observability.context import RunContext


MAX_ITERATIONS = 3


def route_after_review(state: GraphState):
    """Decide the next graph node after the `reviewer` node.

    - If the review passed, continue to the `verifier` node.
    - If the iteration limit was reached, end the run.
    - Otherwise, route back to `coder` for another iteration.

    The function signature matches what `StateGraph.add_conditional_edges`
    expects: it receives the current `state` and returns the next node key or
    `END`.
    """
    if state.get("review_passed"):
        return "verifier"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return END
    return "coder"


def route_after_verification(state: GraphState):
    """Decide the next graph node after the `verifier` node.

    - If verification passed, proceed to the `file_writer` node.
    - If the iteration limit was reached, end the run.
    - Otherwise, retry by routing to `coder`.
    """
    if state.get("verification_passed"):
        return "file_writer"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return END
    return "coder"


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

    # Register nodes from the `nodes` module. Using a clear module alias
    # (`nodes_module`) improves readability compared to a generic name.
    builder.add_node("file_reader", _wrap(file_reader_node))
    builder.add_node("context_builder", _wrap(context_builder_node))
    builder.add_node("coder", _wrap(coder_node))
    builder.add_node("diff_generator", _wrap(diff_generator_node))
    builder.add_node("reviewer", _wrap(reviewer_node))
    builder.add_node("verifier", _wrap(verifier_node))
    builder.add_node("file_writer", _wrap(file_writer_node))

    # Linear topology with conditional edges for retry/looping behavior
    builder.add_edge(START, "file_reader")
    builder.add_edge("file_reader", "context_builder")
    builder.add_edge("context_builder", "coder")
    builder.add_edge("coder", "diff_generator")
    builder.add_edge("diff_generator", "reviewer")
    builder.add_edge("reviewer", "verifier")
    builder.add_edge("verifier", "file_writer")
    builder.add_edge("file_writer", END)

    builder.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "coder": "coder",
            "verifier": "verifier",
            "file_writer": "file_writer",
            END: END,
        },
    )

    builder.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "coder": "coder",
            "file_writer": "file_writer",
            END: END,
        },
    )

    return builder.compile()
