from langgraph.graph import StateGraph, START, END

from src.graph.state import GraphState
from src.graph.nodes.nodes import coder_node, reviewer_node


def route_after_review(state: GraphState):
    if state.get("review_passed"):
        return END
    return "coder"


builder = StateGraph(GraphState)

builder.add_node("coder", coder_node)
builder.add_node("reviewer", reviewer_node)

builder.add_edge(START, "coder")
builder.add_edge("coder", "reviewer")

builder.add_conditional_edges(
    "reviewer",
    route_after_review,
    {
        "coder": "coder",
        END: END,
    },
)

graph = builder.compile()