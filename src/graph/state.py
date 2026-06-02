from typing import TypedDict, NotRequired

from src.retrieval.contracts.context_contract import RepositoryContextPayload
from src.retrieval.contracts.retrieval_contract import RetrievalResult
from src.scheduler.task_request import TaskRequest


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

    # Original request contract; populated by GraphStateFactory.
    # Nodes should prefer reading structured fields from here over individual
    # string keys once the retrieval pipeline is wired up.
    task_request: NotRequired[TaskRequest]

    # Target file path (added for repository-aware execution)
    target_file: NotRequired[str]

    # All files selected by planner_node to be modified (1–3 entries).
    # target_file is always chosen[0]; this list is kept for future multi-file looping.
    target_files: NotRequired[list[str]]

    # Set by planner_node when no suitable file is found; causes the run to terminate.
    planner_error: NotRequired[str]

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

    # Structured output from the retrieval pipeline. Downstream nodes should
    # eventually consume this instead of individual selected_file_ids / target_file keys.
    retrieval_result: NotRequired[RetrievalResult]

    # --- Static validator structured output ---

    # True if ast.compile passed.
    syntax_ok: NotRequired[bool]

    # True if ruff passed (or ruff was not available).
    lint_ok: NotRequired[bool]

    # Individual error strings from syntax or lint checks.
    review_errors: NotRequired[list[str]]

    # --- Verifier structured output ---

    # True when the code executed without exceptions.
    runtime_ok: NotRequired[bool]

    # Categorised error type, e.g. "SyntaxError", "ImportError", "RuntimeError".
    error_type: NotRequired[str]

    # Raw stderr captured from subprocess execution.
    verifier_stderr: NotRequired[str]

    # Raw stdout captured from subprocess execution.
    verifier_stdout: NotRequired[str]

    # --- Semantic validator output ---

    # True when task_alignment_score meets or exceeds the configured threshold.
    semantic_passed: NotRequired[bool]

    # Formatted failure summary forwarded to coder_node on retry.
    semantic_feedback: NotRequired[str]

    # 0.0–1.0 score of how well the code satisfies the task intent.
    task_alignment_score: NotRequired[float]

    # Requirements from the task that are absent in the generated code.
    missing_requirements: NotRequired[list[str]]

    # Behaviours in the generated code that contradict the task.
    incorrect_behaviors: NotRequired[list[str]]

    # Changes made that were not requested by the task.
    unnecessary_changes: NotRequired[list[str]]

    # Free-form observations from the semantic validator LLM.
    semantic_notes: NotRequired[str]

    # 0.0–1.0 confidence in the above evaluation.
    semantic_confidence: NotRequired[float]

    # 0.0–1.0 estimate of how likely the change breaks existing behaviour outside
    # the task scope. Populated by semantic_validator_node; factored into pass/fail.
    regression_risk: NotRequired[float]

    # --- Multi-file execution plan ---

    # "single_file" when only one file needs modification; "multi_file" otherwise.
    # Set by dependency_analyzer_node.
    plan_scope: NotRequired[str]

    # Full set of files that need modification, determined by dependency_analyzer_node.
    # Ordered: definition files first, importer files after.
    affected_files: NotRequired[list[str]]

    # Ordered list of ChangePlanStep dicts produced by change_planner_node.
    # Each step: {file, operation, symbol, change, reason}.
    change_plan: NotRequired[list[dict]]

    # Index of the NEXT step to execute (0-based). Incremented by plan_dispatcher_node.
    current_plan_step: NotRequired[int]

    # The ChangePlanStep dict currently being executed. Set by plan_dispatcher_node so
    # coder_node can include the specific symbol/change instruction without re-indexing.
    active_plan_step: NotRequired[dict]

    # Absolute paths of files successfully written so far in the current plan.
    # Accumulated by plan_dispatcher_node; staged as a group by git_committer_node.
    modified_files: NotRequired[list[str]]

    # True for all non-final steps in a multi-file plan.
    # When set, route_after_verification treats RuntimeError as a pass-through
    # (expected during cross-file edits where the repo is in a transitional state).
    is_intermediate_step: NotRequired[bool]

    # Set when a plan step fails all retry cycles mid-plan.
    # git_committer_node includes a partial-completion note in the commit message.
    plan_failed: NotRequired[bool]

    # True when target_file was supplied by the caller rather than chosen by the LLM.
    # Causes route_after_planner to bypass dependency_analyzer and go directly to file_reader.
    explicit_target_file: NotRequired[bool]

    # --- Git fields ---

    # Branch created for this task, e.g. "feature/fix-auth-bug"
    branch_name: NotRequired[str]

    # Git HEAD SHA at graph resolution time; also used as retrieval anchor.
    repo_sha: NotRequired[str]

    # Full hex SHA of the commit created by git_committer_node; empty string
    # when no commit was made (file unchanged or committer skipped).
    commit_sha: NotRequired[str]
