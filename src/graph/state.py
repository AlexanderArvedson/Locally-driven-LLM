from typing import TypedDict, NotRequired

from src.retrieval.contracts.context_contract import RepositoryContextPayload


class GraphState(TypedDict):
    """
    Shared state passed between LangGraph nodes.

    This state represents a single execution cycle in the maintenance workflow,
    where a task is processed, code is generated, and optionally reviewed.

    Rule: state must only carry lightweight references and metadata.
    Heavy objects (RepositorySnapshot, GraphHandle) are constructed locally
    inside the nodes that need them and never stored here.
    """

    # Task selected by the user (e.g. "refactor this function", "write tests")
    task: str

    # Target file path (added for repository-aware execution)
    target_file: NotRequired[str]

    # Repository root path used for deterministic snapshot creation
    repo_path: NotRequired[str]

    # Absolute path to the resolved graphify-out/ directory for the target repo.
    # Set by graph_resolver_node; consumed by retrieval_node.
    graph_path: NotRequired[str]

    # Original code content from the target file before modification
    original_code: NotRequired[str]

    # Code generated or modified by the LLM
    generated_code: NotRequired[str]

    # Final updated version after potential review iteration
    updated_code: NotRequired[str]

    # Feedback from the review node, if any issues are detected
    review_feedback: NotRequired[str]

    # Number of review cycles completed (used for retry loops)
    iteration: NotRequired[int]

    # Whether the latest review passed successfully
    review_passed: NotRequired[bool]

    # Set by file_writer_node and verifier_node to signal write/verify outcomes.
    verification_passed: NotRequired[bool]
    verification_feedback: NotRequired[str]

    # --- Retrieval references (lightweight) ---

    # UUID for the retrieval session that produced the current context.
    retrieval_session_id: NotRequired[str]

    # Repo-relative paths of the files selected by the retrieval pipeline.
    selected_file_ids: NotRequired[list[str]]

    # Git HEAD SHA of the graph snapshot used during retrieval.
    # Empty string when retrieval fell back to the heuristic ranker.
    graph_snapshot_sha: NotRequired[str]

    # --- Context for LLM (bounded, derived by retrieval_node) ---

    # Versioned, deterministic context payload consumed by coder_node.
    repository_context: NotRequired[RepositoryContextPayload]

    # Full contents of up to 5 related files, capped at 3 000 chars each.
    # Populated by retrieval_node; consumed by coder_node for prompt context.
    related_file_contents: NotRequired[dict[str, str]]

    # --- Git fields ---

    # Branch created for this task, e.g. "feature/fix-auth-bug"
    branch_name: NotRequired[str]

    # Git HEAD SHA at graph resolution time; also used as retrieval anchor.
    repo_sha: NotRequired[str]
