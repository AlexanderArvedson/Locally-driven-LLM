from langgraph.graph import StateGraph, START, END

from src.graph.state import GraphState
from src.graph.nodes.nodes import coder_node, file_reader_node, file_writer_node, reviewer_node

MAX_ITERATIONS = 3


def route_after_review(state: GraphState):
    if state.get("review_passed"):
        return "file_writer"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return END
    return "coder"


builder = StateGraph(GraphState)

builder.add_node("file_reader", file_reader_node)
builder.add_node("coder", coder_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("file_writer", file_writer_node)

builder.add_edge(START, "file_reader")
builder.add_edge("file_reader", "coder")
builder.add_edge("coder", "reviewer")
builder.add_edge("file_writer", END)

builder.add_conditional_edges(
    "reviewer",
    route_after_review,
    {
        "coder": "coder",
        "file_writer": "file_writer",
        END: END,
    },
)

graph = builder.compile()