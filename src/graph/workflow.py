from langgraph.graph import StateGraph, START, END

from src.graph.state import GraphState
from src.graph.nodes.nodes import coder_node


builder = StateGraph(GraphState)

builder.add_node("coder", coder_node)

builder.add_edge(START, "coder")
builder.add_edge("coder", END)

graph = builder.compile()