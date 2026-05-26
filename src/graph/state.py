from typing import TypedDict, NotRequired, Any

from src.repository.repository_types import ContextPackage, RepositorySnapshot


class GraphState(TypedDict):
    """
    Shared state passed between LangGraph nodes.

    This state represents a single execution cycle in the maintenance workflow,
    where a task is processed, code is generated, and optionally reviewed.
    """

    # Task selected by the user (e.g. "refactor this function", "write tests")
    task: str

    # Target file path (added for repository-aware execution)
    target_file: NotRequired[str]

    # Repository root path used for deterministic snapshot creation
    repo_path: NotRequired[str]

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

    # Future expansion:
    # context: NotRequired[str]
    # passed: NotRequired[bool]
    # model_used: NotRequired[str]
    # messages: NotRequired[list[dict]]
    # diff: NotRequired[str]
    # embeddings: NotRequired[list[float]]

    # Repository-aware additions
    repository_context: NotRequired[dict[str, Any]]
    repository_snapshot: NotRequired[RepositorySnapshot]