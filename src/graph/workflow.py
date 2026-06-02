"""Graph construction helpers for the file-edit workflow.

This module builds a `StateGraph` for the file-edit workflow and provides a
factory `make_graph(run_context)` that returns a compiled graph wired so each
node receives the provided `RunContext` instance.

Observability is intentionally separated from `GraphState`; the graph factory
binds the runtime `run_context` into node callables using a small wrapper so
the graph runtime can continue to invoke nodes with the single-argument
signature it expects.

Multi-file execution path:
  retrieval → planner → dependency_analyzer → change_planner
  → plan_dispatcher → file_reader → coder → diff_generator → reviewer
  → semantic_validator → file_writer ─┐
          ↑                            │ (more steps)
          └────────────────────────────┘
                                       │ (done)
                                git_committer → END

Single-file execution path (unchanged):
  retrieval → planner → [dep_analyzer: single_file] → file_reader → coder
  → diff_generator → reviewer → semantic_validator → file_writer
  → git_committer → END

Explicit target_file path (user-supplied, bypasses dependency analysis):
  retrieval → planner → file_reader → coder → … → file_writer → git_committer → END
"""

from langgraph.graph import StateGraph, START, END

from src.graph.state import GraphState
from src.graph.nodes import node_index as nodes_module
from src.config_loader import get_max_workflow_revision_cycles
from src.observability.context import RunContext


def _exhaustion_target(state: GraphState) -> str:
    """Return the next node when the retry-cycle limit is hit.

    For multi-file plans, routes to git_committer so any already-written files
    are committed before the run ends. For single-file tasks, ends immediately.
    """
    return "git_committer" if state.get("change_plan") else END


def route_after_review(state: GraphState):
    """Decide the next node after the reviewer (static_validator) node."""
    if state.get("review_passed"):
        return "semantic_validator"
    if state.get("iteration", 0) >= get_max_workflow_revision_cycles(state.get("repo_path")):
        return _exhaustion_target(state)
    return "coder"


def route_after_semantic(state: GraphState):
    """Decide the next node after the semantic_validator node."""
    if state.get("semantic_passed"):
        return "file_writer"
    if state.get("iteration", 0) >= get_max_workflow_revision_cycles(state.get("repo_path")):
        return _exhaustion_target(state)
    return "coder"


def route_after_planner(state: GraphState):
    """Route after planner based on whether a target was explicitly supplied.

    - planner_error → END (no suitable file found)
    - explicit_target_file → file_reader (user-supplied path; skip dependency analysis)
    - otherwise → dependency_analyzer
    """
    if state.get("planner_error"):
        return END
    if state.get("explicit_target_file"):
        return "file_reader"
    return "dependency_analyzer"


def route_after_dependency_analyzer(state: GraphState):
    """Route after dependency analysis based on plan scope.

    - planner_error → END (dependency analysis failed)
    - multi_file → change_planner
    - single_file → file_reader (no plan needed)
    """
    if state.get("planner_error"):
        return END
    if state.get("plan_scope") == "multi_file":
        return "change_planner"
    return "file_reader"


def route_after_change_planner(state: GraphState):
    """Terminate early if the change planner could not produce a valid plan."""
    if state.get("planner_error"):
        return END
    return "plan_dispatcher"


def route_after_file_writer(state: GraphState):
    """Decide the next node after a file is written.

    - plan_failed → git_committer (disk I/O failure; commit whatever was written)
    - more plan steps remain → plan_dispatcher
    - otherwise → git_committer (plan complete or single-file run)
    """
    if state.get("plan_failed"):
        return "git_committer"
    plan = state.get("change_plan") or []
    if plan and state.get("current_plan_step", 0) < len(plan):
        return "plan_dispatcher"
    return "git_committer"


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

    # --- Existing nodes ---
    builder.add_node("branch_creator",    _wrap(nodes_module.branch_creator_node))
    builder.add_node("graph_resolver",    _wrap(nodes_module.graph_resolver_node))
    builder.add_node("retrieval",         _wrap(nodes_module.retrieval_node))
    builder.add_node("planner",           _wrap(nodes_module.planner_node))
    builder.add_node("file_reader",       _wrap(nodes_module.file_reader_node))
    builder.add_node("coder",             _wrap(nodes_module.coder_node))
    builder.add_node("diff_generator",    _wrap(nodes_module.diff_generator_node))
    builder.add_node("reviewer",          _wrap(nodes_module.static_validator_node))
    builder.add_node("semantic_validator", _wrap(nodes_module.semantic_validator_node))
    builder.add_node("file_writer",       _wrap(nodes_module.file_writer_node))
    builder.add_node("git_committer",     _wrap(nodes_module.git_committer_node))

    # --- New multi-file nodes ---
    builder.add_node("dependency_analyzer", _wrap(nodes_module.dependency_analyzer_node))
    builder.add_node("change_planner",      _wrap(nodes_module.change_planner_node))
    builder.add_node("plan_dispatcher",     _wrap(nodes_module.plan_dispatcher_node))

    # --- Fixed edges (same for all paths) ---
    builder.add_edge(START,            "branch_creator")
    builder.add_edge("branch_creator", "graph_resolver")
    builder.add_edge("graph_resolver", "retrieval")
    builder.add_edge("retrieval",      "planner")
    builder.add_edge("file_reader",    "coder")
    builder.add_edge("coder",          "diff_generator")
    builder.add_edge("diff_generator", "reviewer")
    builder.add_edge("git_committer",  END)

    # Multi-file plan: change_planner → plan_dispatcher → file_reader (loop entry)
    builder.add_edge("plan_dispatcher", "file_reader")

    # --- Conditional edges ---

    # Planner: route based on whether target_file was explicitly supplied.
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "dependency_analyzer": "dependency_analyzer",
            "file_reader": "file_reader",
            END: END,
        },
    )

    # Dependency analyzer: single vs multi-file scope.
    builder.add_conditional_edges(
        "dependency_analyzer",
        route_after_dependency_analyzer,
        {
            "change_planner": "change_planner",
            "file_reader": "file_reader",
            END: END,
        },
    )

    # Change planner: only fails if LLM returns unusable output.
    builder.add_conditional_edges(
        "change_planner",
        route_after_change_planner,
        {
            "plan_dispatcher": "plan_dispatcher",
            END: END,
        },
    )

    # Reviewer (static validator): retry or advance to semantic validation.
    builder.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "coder": "coder",
            "semantic_validator": "semantic_validator",
            "git_committer": "git_committer",
            END: END,
        },
    )

    # Semantic validator: retry or write.
    builder.add_conditional_edges(
        "semantic_validator",
        route_after_semantic,
        {
            "coder": "coder",
            "file_writer": "file_writer",
            "git_committer": "git_committer",
            END: END,
        },
    )

    # File writer: advance to next plan step, or commit everything.
    builder.add_conditional_edges(
        "file_writer",
        route_after_file_writer,
        {
            "plan_dispatcher": "plan_dispatcher",
            "git_committer": "git_committer",
        },
    )

    return builder.compile()
