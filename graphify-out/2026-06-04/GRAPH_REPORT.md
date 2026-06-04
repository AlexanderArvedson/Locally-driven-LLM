# Graph Report - Locally-driven-langgraph-LLM  (2026-06-04)

## Corpus Check
- 71 files · ~23,894 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 954 nodes · 1971 edges · 79 communities (63 shown, 16 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 388 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2d1ac9b5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Graph State Data Flow|Graph State Data Flow]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Repository Context & Graph State|Repository Context & Graph State]]
- [[_COMMUNITY_Test Infrastructure & Fixtures|Test Infrastructure & Fixtures]]
- [[_COMMUNITY_Design Contracts & Project Plan|Design Contracts & Project Plan]]
- [[_COMMUNITY_LLM Pipeline & Sandbox|LLM Pipeline & Sandbox]]
- [[_COMMUNITY_Repository Indexer Protocol|Repository Indexer Protocol]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Simple Repo Fixture|Simple Repo Fixture]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Infrastructure & Docs|Infrastructure & Docs]]
- [[_COMMUNITY_Sample Repo v2 Docs|Sample Repo v2 Docs]]
- [[_COMMUNITY_Node Package Init|Node Package Init]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Repository Package Init|Repository Package Init]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Runtime Directory|Runtime Directory]]
- [[_COMMUNITY_Phase 5 Advanced Maintenance|Phase 5 Advanced Maintenance]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]

## God Nodes (most connected - your core abstractions)
1. `GraphState` - 74 edges
2. `RunContext` - 68 edges
3. `FunctionRecord` - 37 edges
4. `PipelineConfig` - 35 edges
5. `get_repository_config()` - 32 edges
6. `emit_success()` - 31 edges
7. `emit_failure()` - 30 edges
8. `Neo4jStore` - 29 edges
9. `OllamaClient` - 27 edges
10. `RepositorySnapshot` - 27 edges

## Surprising Connections (you probably didn't know these)
- `ExecutionLoop` --implements--> `Phase 3 - Async Execution Coordinator`  [INFERRED]
  src/scheduler/loop.py → docs/PROJECT_PLAN.md
- `diff_generator_node()` --implements--> `Phase 1 - File Mutation MVP`  [INFERRED]
  src/graph/nodes/diff_generator.py → docs/PROJECT_PLAN.md
- `WorkflowExecutor` --implements--> `WorkflowExecutor as Single Orchestration Boundary`  [INFERRED]
  src/scheduler/executor.py → docs/PROJECT_PLAN.md
- `TaskQueue` --implements--> `FIFO Task Queue - In-memory Deterministic Ordering`  [INFERRED]
  src/scheduler/queue.py → docs/PROJECT_PLAN.md
- `TaskType (passive|active)` --conceptually_related_to--> `Active Mode - User-triggered Code Modification`  [INFERRED]
  src/scheduler/task.py → docs/PROJECT_PLAN.md

## Hyperedges (group relationships)
- **Test infrastructure: httpx_stub + fixture_repo used across multiple test suites** — support_httpx_stub_httpx_stub, support_fixture_repo_temporary_fixture_repo, tests_test_context_builder_node_testcontextbuildernode, tests_test_coder_prompt_contract_testcoderpromptcontract, tests_test_retrieval_integration_testretrievalintegration, tests_test_retrieval_engine_testretrievalengine [EXTRACTED 1.00]
- **Retrieval pipeline tests: indexer + retrieval engine + context builder** — tests_test_repository_indexer_testrepositoryindexer, tests_test_retrieval_engine_testretrievalengine, tests_test_context_builder_testcontextbuilder, tests_test_context_builder_node_testcontextbuildernode, tests_test_retrieval_integration_testretrievalintegration, concept_retrieval_pipeline [INFERRED 0.95]
- **ExecutionLoop correctness tests: ordering, exclusivity, passive vs active tasks** — tests_test_execution_coordinator_recordingworkflowexecutor, tests_test_execution_coordinator_test_active_tasks, tests_test_execution_coordinator_test_mutation_exclusivity, tests_test_execution_coordinator_test_passive_tasks, concept_execution_loop [EXTRACTED 1.00]
- **sample_repo_v2 fixture: main → task_runner → task_service / report_service / validators** — fixture_sample_repo_v2_main_main, fixture_task_runner_run_task_pipeline, fixture_task_runner_load_seed_payloads, fixture_adapter_legacytaskadapter [EXTRACTED 1.00]
- **Fixture Task Validation and Normalization Pipeline** — utils_validators_validate_task_payload, utils_validators_normalize_task_payload, utils_validators_normalize_task, utils_validators_normalize_task_record, models_task_task, utils_date_helpers_parse_due_date, utils_date_helpers_format_due_date [INFERRED 0.85]
- **Fixture Report Building and Rendering Pipeline** — services_report_service_reportservice_build_report, services_report_service_reportservice_render_report, utils_formatting_format_task_line, utils_formatting_format_report_header, utils_formatting_format_totals_line, models_report_taskreport, models_task_task [INFERRED 0.85]
- **Config Constants Consumers** — src_config_ollama_base_url, src_config_coder_model, src_config_max_iterations, scripts_test_ollama_main [EXTRACTED 0.95]
- **LangGraph Pipeline: All Node Functions** — nodes_file_reader_file_reader_node, nodes_context_builder_context_builder_node, nodes_coder_coder_node, nodes_reviewer_reviewer_node, nodes_verifier_verifier_node, nodes_file_writer_file_writer_node [EXTRACTED 1.00]
- **GraphState: Shared State Fields Across Nodes** — graph_state_graphstate, concept_state_field_original_code, concept_state_field_generated_code, concept_state_field_repository_context, concept_state_field_repository_snapshot, concept_state_field_review_passed, concept_state_field_verification_passed [EXTRACTED 1.00]
- **Repository Layer: Core Data Types** — repository_repository_types_symbol, repository_repository_types_dependencyedge, repository_repository_types_filenode, repository_repository_types_repositorysnapshot, repository_repository_types_contextpackage [EXTRACTED 1.00]
- **Sandbox Execution Subsystem** — tools_sandbox_run_code_in_sandbox, tools_sandbox_runner_main, concept_sandbox_execution [EXTRACTED 1.00]
- **Node Support Utilities Used by Multiple Nodes** — nodes_support_require_state_value, nodes_support_strip_code_fences, nodes_support_validate_python_syntax, nodes_support_select_target_file_from_repo_path, nodes_support_client [INFERRED 0.95]
- **Context Building Chain: Indexer -> Retrieval -> ContextBuilder -> Contract** — repository_simple_repository_indexer_simplerepositoryindexer, repository_retrieval_engine_simpleretrievalengine, repository_context_contract_build_repository_context_payload, nodes_context_builder_context_builder_node [INFERRED 0.95]
- **Scheduler Core Components (ExecutionLoop, TaskQueue, WorkflowExecutor, Task)** — scheduler_loop_executionloop, scheduler_queue_taskqueue, scheduler_executor_workflowexecutor, scheduler_task_task [EXTRACTED 1.00]
- **Observability Pipeline (RunContext -> emit_event -> log_event -> JSONL)** — observability_context_runcontext, observability_event_logging_utils_emit_event, observability_event_logging_utils_emit_success, observability_event_logging_utils_emit_failure, observability_logger_log_event [INFERRED 0.95]
- **Scheduler Execution Flow (submit -> enqueue -> consume -> execute graph)** — scheduler_loop_executionloop_submit_task, scheduler_queue_taskqueue_enqueue, scheduler_loop_executionloop_consume, scheduler_queue_taskqueue_dequeue, scheduler_executor_workflowexecutor_execute [INFERRED 0.95]
- **Project Development Phases (Phase 1-5)** — docs_project_plan_phase1_file_mutation_mvp, docs_project_plan_phase2_repo_awareness, docs_project_plan_phase3_async_execution, docs_project_plan_phase4_passive_analysis, docs_project_plan_phase5_advanced_maintenance [EXTRACTED 1.00]
- **Context Contract Components (version, payload, determinism, prompt rendering)** — docs_context_contract_context_version, docs_context_contract_payload_shape, docs_context_contract_determinism_rules, docs_context_contract_prompt_rendering [EXTRACTED 1.00]

## Communities (79 total, 16 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.22
Nodes (7): BudgetAllocation, Context window budget allocation.  ContextBudget enforces per-file character lim, Result of a budget allocation pass., Result of a budget allocation pass.      Attributes:         selected_files: Ord, Return the largest prefix of `ranked_files` that fits the budget.          Tar, Return the largest prefix of `ranked_files` that fits within all limits., str

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (55): LanguageSlicer, Node, Parser, Symbol-level context slicing for language-agnostic code extraction., LanguageSlicer, Language-agnostic slicing Protocol.  Defines the shared contract that every lang, Everything extracted about one symbol from a source file., Extract and stitch back a named symbol within a source file. (+47 more)

### Community 2 - "Repository Context & Graph State"
Cohesion: 0.22
Nodes (8): Create a fresh RunContext with a new UUID4 run_id., Create a fresh RunContext with a new UUID4 run_id and current timestamp., format_run_console(), Write the aggregated run object to `.runtime/runs/<run_id>.json`.      Produces, Return a human-readable execution trace string for console output.      Produces, write_run_summary(), str, Task

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.20
Nodes (16): DependencyEdge, FileNode, Core data types shared across the retrieval pipeline.  Defines the immutable sna, Represents a top-level symbol extracted from a file., Represents a directed import relationship between files., Metadata for a single file in the repository snapshot., Symbol, DependencyEdge (+8 more)

### Community 4 - "Design Contracts & Project Plan"
Cohesion: 0.50
Nodes (4): Convert absolute paths to repo-relative strings when possible., Convert absolute paths to repo-relative strings when possible., Convert absolute paths to repo-relative strings when possible., _to_relative_ids()

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.13
Nodes (18): EmbedResult, _gpu_layers(), LLMResult, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal `, Send an embedding request to the Ollama API and return the vector.          Args, Return the Ollama ``num_gpu`` value for a given ``allow_gpu`` flag.      Ollama, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Create a new `OllamaClient`.          Args:             base_url: Base URL of (+10 more)

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.15
Nodes (10): Map resolved absolute file paths to their highest node score.          Nodes wit, Like `files_for_nodes` but preserves per-node scores.          Maps each absolut, Extract normalised, non-stopword tokens from a task string., Load graph.json from `graph_dir` and return a GraphQuery instance.          Read, Return (node_id, score) pairs ranked by keyword overlap with task words., BFS expansion: return all node_ids reachable within `hops` edges.          Inclu, float, int (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (39): CompletedProcess, _auth_url(), branch_exists(), build_branch_name(), clone_if_missing(), commit_file(), create_task_branch(), get_diff_stat() (+31 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (47): GraphHandle, Immutable reference to a resolved, validated knowledge graph.      Produced excl, GraphConfig, GraphHandle, _build_graph(), _compute_repo_id(), _get_head_sha(), graph_resolver_node() (+39 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (21): OllamaClient, PipelineResult, Summary of a completed pipeline run., Summary of a completed pipeline run., DescriptionService, Generates structured JSON descriptions of functions via OllamaClient., Generates structured JSON descriptions of functions via OllamaClient., EmbeddingService (+13 more)

### Community 12 - "Simple Repo Fixture"
Cohesion: 0.17
Nodes (19): AppConfig, get_coder_model(), get_coder_model_config(), get_ollama_base_url(), get_primary_model(), get_semantic_model_config(), ModelConfig, str (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (20): bool, Static validator node.  Replaces the former reviewer node. Responsibilities are, Validate generated code for structural correctness.      Runs Python syntax vali, static_validator_node(), Shared helpers for graph node implementations., Return a required value from `state` or raise ValueError., Remove a single pair of surrounding Markdown code fences., Validate that `content` compiles as Python. (+12 more)

### Community 20 - "Community 20"
Cohesion: 0.38
Nodes (6): create_pull_request(), _parse_owner_repo(), GitHub pull request creation via the REST API., Extract (owner, repo) from a GitHub remote URL., Create a GitHub pull request and return its HTML URL.      Args:         remote_, str

### Community 26 - "Community 26"
Cohesion: 0.22
Nodes (9): GraphState: original_code field, _build_context_slice(), file_reader_node(), Read the target file (or select one) and return its contents.      Expected stat, Read the target file and, when a target symbol is set, build a context slice., Assemble the context dict for the coder's focused prompt., GraphState, RunContext (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.29
Nodes (7): get_semantic_threshold(), float, Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass.

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (18): Git committer node.  Stages the modified target file and creates a git commit on, Planner node — selects which file(s) to modify from retrieval candidates.  When, emit_event(), emit_failure(), emit_success(), Small helper utilities for observability event emission.  Provides helpers to em, Emit a single observability event with consistent shape.      Args:         r, Emit a single compact observability event.      Args:         run_context: The R (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.19
Nodes (15): ContextAssembler, Deterministic, capped context assembler that consumes a snapshot.      Returns a, ContextBudget, Allocates ranked files against char and file-count limits.      Limits are adv, Allocates ranked files against char-per-file, file-count, and token limits., Retrieval node — orchestrates the graph-backed retrieval pipeline.  Pipeline sta, Build repository context for the current task and target file.      Retrieval, Build repository context for the current task and target file.      Retrieval st (+7 more)

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (21): RepositoryContextPayload, Output contract from the retrieval pipeline, stored in GraphState.      Downstre, Input contract passed from the scheduler layer to the retrieval pipeline., RetrievalRequest, RetrievalResult, GraphState, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a sing (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.23
Nodes (6): FIFO Task Queue - In-memory Deterministic Ordering, ExecutionLoop, Background execution loop that consumes tasks from a `TaskQueue`.      Responsib, TaskQueue, Task, Task

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (7): GraphStateFactory, Build the initial GraphState from a validated TaskRequest., Converts an external TaskRequest into the internal GraphState.      This is the, External request contract for submitting a task to the workflow.      Separates, TaskRequest, GraphState, TaskRequest

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (27): GraphState: review_passed field, GraphState: verification_passed field, make_graph(), Graph construction helpers for the file-edit workflow.  This module builds a `St, Decide the next graph node after the `reviewer` (static_validator) node.      -, Decide the next graph node after the `semantic_validator` node.      - If semant, Terminate early when the planner found no file to modify., Decide the next graph node after the `semantic_validator` node.      - If semant (+19 more)

### Community 36 - "Community 36"
Cohesion: 0.20
Nodes (10): Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json. (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (9): Sandbox Subprocess Execution Pattern, int, str, int, str, Helper API to run untrusted/generated Python code in a subprocess sandbox.  This, Run `code` in a subprocess with limits.      Args:         code: Python source t, run_code_in_sandbox() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.13
Nodes (17): _parse_file_list(), _parse_planner_response(), planner_node(), Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Parse a JSON array from LLM output, filtering to known candidate paths. (+9 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (19): diff_generator_node(), Compute a unified diff between the original and generated code.      Expected st, build_ast_graph(), graphify_indexer_node(), Graphify indexer — internal graph-building utility.  Provides `build_ast_graph`,, Run AST-only graphify extraction and write graph.json to graph_dir., Build or refresh the graphify knowledge graph for the target repository., Run AST-only graphify extraction and write graph.json to graph_dir. (+11 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (11): branch_creator_node(), Branch creator node.  Creates (or checks out) a task branch in the target reposi, Create a task branch in the target repository.      Reads ``repo_path`` and ``ta, git_committer_node(), Stage and commit the modified target file.      Expected state keys:     - ``, Stage and commit the modified target file.      Expected state keys:     - ``rep, Aggregate export surface for graph nodes., GraphState (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (10): get_repository_config(), Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no rep (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.27
Nodes (17): Any, Path, load_config(), _load_model_config(), _load_planner_config(), _load_repository_config(), Any, Path (+9 more)

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (8): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Bounded Autonomy Design Principle, Mutation Exclusivity - One Active Workflow at a Time, Phase 2 - Repository Awareness, Phase 3 - Async Execution Coordinator

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (14): get_retrieval_config(), _load_retrieval_config(), Parse the ``retrieval`` sub-object from a repository config entry.      All fi, Parse the ``retrieval`` sub-object from a repository config entry.      All fi, Parse the ``retrieval`` sub-object from a repository config entry.      All fi, Parse the ``retrieval`` sub-object from a repository config entry.      All fiel, Return retrieval limits and behavior for the repository matching ``repo_path``., Return retrieval limits and behavior for the repository matching ``repo_path``. (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (11): get_planner_config(), PlannerConfig, Global system-level settings shared across all repositories.      Attributes:, Return planner settings for the repository matching ``repo_path``., Return planner settings for the repository matching ``repo_path``., Global system-level settings shared across all repositories.      Attributes:, Global system-level settings shared across all repositories.      Attributes:, Controls how many files the planner node may select for modification.      Att (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (24): bytes, bool, Path, str, str, atomic_write_bytes(), _detect_crlf(), Return True if the file contains CRLF line endings. (+16 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (9): _heuristic_rank(), Fallback ranking when graph is unavailable., Fallback ranking when graph is unavailable., Read bounded file contents for the coder prompt, excluding target file., Read bounded file contents for the coder prompt, excluding target file., Fallback ranking when graph is unavailable., Read bounded file contents for the coder prompt, excluding target file., _read_related_files() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.29
Nodes (6): WorkflowExecutor as Single Orchestration Boundary, Executor that runs a workflow graph for a given `Task`.      The executor acce, Executor that runs a workflow graph for a given `Task`.      The executor accept, WorkflowExecutor, TaskQueue, WorkflowExecutor

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (7): _load_graph_config(), Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults to

### Community 52 - "Community 52"
Cohesion: 0.33
Nodes (6): get_semantic_model(), Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semantic_

### Community 53 - "Community 53"
Cohesion: 0.40
Nodes (5): Active Mode - User-triggered Code Modification, Passive Mode - Continuous Repository Analysis, Phase 1 - File Mutation MVP, Phase 4 - Passive Analysis System, TaskType (passive|active)

### Community 54 - "Community 54"
Cohesion: 0.28
Nodes (15): Neo4jStore, Neo4jConfig, Neo4jStore, Async Neo4j driver wrapper for Function nodes and SIMILAR_TO edges., Async Neo4j driver wrapper for Function nodes and SIMILAR_TO edges., _build_report(), generate_report(), Post-run report generator.  Queries Neo4j after a pipeline run and writes a mark (+7 more)

### Community 55 - "Community 55"
Cohesion: 0.21
Nodes (13): ContextAssemblerProtocol, Context assembler — builds bounded ContextPackage from ranked files.  ContextAss, Interface for bounded context assembly., Build and return a bounded ContextPackage.          Must be deterministic and mu, ContextPackage, Immutable snapshot of the repository used for deterministic retrieval., Bounded context package returned by the ContextAssembler.      Contains only lig, RepositorySnapshot (+5 more)

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (7): _load_system_config(), Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~/.

### Community 57 - "Community 57"
Cohesion: 0.25
Nodes (14): GraphState: repository_context field, OllamaClient.chat, _build_full_file_prompt(), _build_symbol_prompt(), coder_node(), _deindent(), _format_contracts(), _format_related_files() (+6 more)

### Community 58 - "Community 58"
Cohesion: 0.21
Nodes (15): build_repository_context_payload(), _dedupe_preserve_order(), DependencySummaryItem, format_repository_context_for_prompt(), _normalize_path(), Versioned contract for retrieval -> coder repository context payloads.  This mod, Validate structural invariants for a repository context payload., Render repository context in a fixed, deterministic prompt section. (+7 more)

### Community 59 - "Community 59"
Cohesion: 0.23
Nodes (8): Repository indexer protocol.  Defines the RepositoryIndexer interface that all i, Interface for repository indexing., Build and return an immutable repository snapshot for `root_path`., Return symbol names for a given file from the snapshot., Return dependency target paths for a given file from the snapshot., RepositoryIndexer, RepositorySnapshot, str

### Community 60 - "Community 60"
Cohesion: 0.30
Nodes (7): HeuristicRanker, Return a deterministic, ordered list of file paths., Deterministic, heuristic-based file ranker.      Ordering rules (score-based, de, bool, int, RepositorySnapshot, str

### Community 61 - "Community 61"
Cohesion: 0.22
Nodes (8): GraphQuery, Graph query utilities for the retrieval pipeline.  GraphQuery loads graph.json o, Loads graph.json once and exposes keyword + dependency queries.      Constructed, GraphQuery, Graph-aware file ranker.  GraphRanker uses a GraphQuery instance to rank file ca, Return an ordered list of file paths relevant to `task`.          Pipeline:, int, str

### Community 62 - "Community 62"
Cohesion: 0.22
Nodes (17): load_pipeline_config(), Pipeline configuration loader.  Reads the top-level ``neo4j`` block and the per-, Load pipeline configuration for a repository.      Args:         config_path: Pa, Load pipeline configuration for a repository.      Args:         config_path: Pa, BatchSizeConfig, ConcurrencyConfig, LimitsConfig, _now_iso() (+9 more)

### Community 63 - "Community 63"
Cohesion: 0.31
Nodes (9): _is_ignored(), Repository file scanner.  Walks a source tree and yields paths to source files w, Return True if any component of the path relative to repo_root is in ignore_name, Return sorted list of source file paths to process.      Args:         repo_path, scan_repository(), _supported_extensions(), bool, Path (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.33
Nodes (5): Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool.

### Community 66 - "Community 66"
Cohesion: 0.19
Nodes (13): FunctionRecord, PipelineConfig, One extracted function or method from a source file., Description service for LLM-generated function summaries.  Wraps ``OllamaClient., Embedding service for code and description vectors.  Wraps ``OllamaClient.embed(, OllamaClient, PipelineConfig, OllamaClient (+5 more)

### Community 67 - "Community 67"
Cohesion: 0.26
Nodes (16): _extract_from_file(), _find_functions(), _get_class_name(), _get_identifier(), _get_property_name(), _is_test_file(), Function extractor.  Uses tree-sitter directly to walk the AST of each source fi, For TS property assignments (``foo = () => ...``), return the property name. (+8 more)

### Community 68 - "Community 68"
Cohesion: 0.18
Nodes (15): ndarray, A SIMILAR_TO relationship between two Function nodes., A SIMILAR_TO relationship between two Function nodes., SimilarityEdge, compute_similarity_edges(), _normalise(), Cosine similarity calculator for function embeddings.  Operates entirely in-memo, L2-normalise each row. Rows with zero norm are left as-is. (+7 more)

### Community 69 - "Community 69"
Cohesion: 0.17
Nodes (9): Embed descriptions for all records in-place, respecting concurrency limit., Embed descriptions for all records in-place, respecting concurrency limit., Populate ``record.code_embedding`` in-place.          Logs and skips on failure, Populate ``record.code_embedding`` in-place.          Logs and skips on failure, Populate ``record.description_embedding`` in-place.          Extracts the ``summ, Embed source code for all records in-place, respecting concurrency limit., Embed source code for all records in-place, respecting concurrency limit., FunctionRecord (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.17
Nodes (10): Generate descriptions for all records in-place, respecting concurrency limit., Remove triple-backtick code fences that models emit despite instructions., Remove triple-backtick code fences that models emit despite instructions., Populate ``record.description`` in-place with a JSON string.          Retries on, Populate ``record.description`` in-place with a JSON string.          Retries on, Generate descriptions for all records in-place, respecting concurrency limit., _strip_fences(), FunctionRecord (+2 more)

### Community 71 - "Community 71"
Cohesion: 0.20
Nodes (9): GraphState: generated_code field, ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All run, Create all required runtime directories if they don't exist.      Uses `parents=, file_writer_node(), Write generated content to disk or apply a unified diff.      Expected state inp, Write generated content to disk or apply a unified diff.      Expected state inp, GraphState (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.20
Nodes (7): Mark functions not in ``seen_ids`` as deleted. Returns count., Mark functions not in ``seen_ids`` as deleted. Returns count., Batch-upsert SIMILAR_TO relationships using UNWIND., Batch-upsert SIMILAR_TO relationships using UNWIND., int, Neo4jConfig, SimilarityEdge

### Community 73 - "Community 73"
Cohesion: 0.22
Nodes (6): Create vector indexes once the embedding dimension is known., Create vector indexes once the embedding dimension is known., Return ``{function_id: source_hash}`` for all live functions in the repo., Batch-upsert Function nodes using UNWIND for efficiency., Batch-upsert Function nodes using UNWIND for efficiency., FunctionRecord

### Community 74 - "Community 74"
Cohesion: 0.25
Nodes (6): LiteralString, _ddl(), Neo4j data store for Function nodes and SIMILAR_TO relationships.  Uses the offi, Idempotently create constraints and indexes.          Args:             vector_d, Idempotently create constraints and indexes.          Args:             vector_d, Format a DDL template with integer-only substitutions and assert LiteralString.

### Community 75 - "Community 75"
Cohesion: 0.29
Nodes (6): Return ``[(id, code_embedding, description_embedding)]`` for all live functions., Return ``[(id, code_embedding, description_embedding)]`` for all live functions., Delete all SIMILAR_TO edges originating from functions in this repo.          Ca, bool, float, str

### Community 76 - "Community 76"
Cohesion: 0.29
Nodes (6): Language, _get_ts_language(), Return one FunctionRecord per function/method found in the repository., Return one FunctionRecord per function/method found in the repository., FunctionRecord, Parser

### Community 77 - "Community 77"
Cohesion: 0.40
Nodes (4): Protocol, RankerProtocol, Heuristic file ranker — deterministic, graph-free retrieval.  HeuristicRanker sc, Interface for file ranking strategies.

## Knowledge Gaps
- **32 isolated node(s):** `float`, `str`, `int`, `str`, `int` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OllamaClient` connect `Community 10` to `Community 64`, `Community 66`, `LLM Pipeline & Sandbox`, `Community 70`, `Community 69`, `Community 19`?**
  _High betweenness centrality (0.346) - this node is a cross-community bridge._
- **Why does `GraphState` connect `Community 30` to `Community 32`, `Community 33`, `Repository Context & Graph State`, `Community 71`, `Community 40`, `Community 9`, `Community 41`, `Community 39`, `Community 48`, `Community 49`, `Community 50`, `Community 19`, `Community 57`, `Community 26`, `Community 28`, `Community 29`?**
  _High betweenness centrality (0.329) - this node is a cross-community bridge._
- **Why does `SymbolSlice` connect `Community 1` to `Community 57`, `Community 26`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `GraphState` (e.g. with `RepositoryContextPayload` and `RetrievalResult`) actually correct?**
  _`GraphState` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 46 inferred relationships involving `RunContext` (e.g. with `GraphConfig` and `GraphHandle`) actually correct?**
  _`RunContext` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `FunctionRecord` (e.g. with `Language` and `LiteralString`) actually correct?**
  _`FunctionRecord` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `PipelineConfig` (e.g. with `Language` and `DescriptionService`) actually correct?**
  _`PipelineConfig` has 28 INFERRED edges - model-reasoned connections that need verification._