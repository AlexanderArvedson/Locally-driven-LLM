from langgraph.graph import StateGraph, START, END

from src.graph.state import GraphState
from src.graph.nodes import nodes as node_impl
from src.observability.context import RunContext

MAX_ITERATIONS = 3


def route_after_review(state: GraphState):
    if state.get("review_passed"):
        return "verifier"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return END
    return "coder"


def route_after_verification(state: GraphState):
    if state.get("verification_passed"):
        return "file_writer"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return END
    return "coder"


def make_graph(run_context: RunContext):
    builder = StateGraph(GraphState)

    # Helper to wrap node implementations so they receive run_context
    def _wrap(node_func):
        async def _wrapped(state):
            return await node_func(state, run_context)

        return _wrapped

    builder.add_node("file_reader", _wrap(node_impl.file_reader_node))
    builder.add_node("coder", _wrap(node_impl.coder_node))
    builder.add_node("diff_generator", _wrap(node_impl.diff_generator_node))
    builder.add_node("reviewer", _wrap(node_impl.reviewer_node))
    builder.add_node("verifier", _wrap(node_impl.verifier_node))
    builder.add_node("file_writer", _wrap(node_impl.file_writer_node))

    builder.add_edge(START, "file_reader")
    builder.add_edge("file_reader", "coder")
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
