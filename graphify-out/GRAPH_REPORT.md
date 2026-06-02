# Graph Report - Locally-driven-langgraph-LLM  (2026-06-02)

## Corpus Check
- 61 files · ~19,482 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 736 nodes · 1545 edges · 59 communities (44 shown, 15 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 281 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `03fb67f0`
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
- [[_COMMUNITY_Patch Application|Patch Application]]
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
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 61|Community 61]]

## God Nodes (most connected - your core abstractions)
1. `GraphState` - 92 edges
2. `RunContext` - 86 edges
3. `emit_success()` - 41 edges
4. `emit_failure()` - 40 edges
5. `get_repository_config()` - 32 edges
6. `require_state_value()` - 30 edges
7. `RepositorySnapshot` - 28 edges
8. `AstIndexer` - 25 edges
9. `str` - 24 edges
10. `GraphQuery` - 23 edges

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

## Communities (59 total, 15 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.22
Nodes (7): BudgetAllocation, Context window budget allocation.  ContextBudget enforces per-file character lim, Result of a budget allocation pass., Result of a budget allocation pass.      Attributes:         selected_files: Ord, Return the largest prefix of `ranked_files` that fits the budget.          Tar, Return the largest prefix of `ranked_files` that fits within all limits., str

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (22): bool, GraphState: generated_code field, file_writer_node(), Write generated content to disk or apply a unified diff.      Expected state inp, Write generated content to disk or apply a unified diff.      Expected state inp, Aggregate export surface for graph nodes., Perform lightweight review checks on generated code.      Performs the following, reviewer_node() (+14 more)

### Community 2 - "Repository Context & Graph State"
Cohesion: 0.23
Nodes (6): FIFO Task Queue - In-memory Deterministic Ordering, ExecutionLoop, Background execution loop that consumes tasks from a `TaskQueue`.      Responsib, TaskQueue, Task, Task

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.06
Nodes (43): ContextAssemblerProtocol, Context assembler — builds bounded ContextPackage from ranked files.  ContextAss, Interface for bounded context assembly., DependencyEdge, FileNode, Core data types shared across the retrieval pipeline.  Defines the immutable sna, Represents a top-level symbol extracted from a file., Represents a top-level symbol extracted from a file. (+35 more)

### Community 4 - "Design Contracts & Project Plan"
Cohesion: 0.15
Nodes (14): _parse_file_list(), planner_node(), Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Parse a JSON array from LLM output, filtering to known candidate paths., Parse a JSON array from LLM output, filtering to known candidate paths., Parse a JSON array from LLM output, filtering to known candidate paths. (+6 more)

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.14
Nodes (15): _gpu_layers(), LLMResult, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal `, Return the Ollama ``num_gpu`` value for a given ``allow_gpu`` flag.      Ollama, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Send a chat request to the Ollama API and return a parsed result.          The, Create a new `OllamaClient`.          Args:             base_url: Base URL of th (+7 more)

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.15
Nodes (10): Map resolved absolute file paths to their highest node score.          Nodes wit, Like `files_for_nodes` but preserves per-node scores.          Maps each absolut, Extract normalised, non-stopword tokens from a task string., Load graph.json from `graph_dir` and return a GraphQuery instance.          Read, Return (node_id, score) pairs ranked by keyword overlap with task words., BFS expansion: return all node_ids reachable within `hops` edges.          Inclu, float, int (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (43): CompletedProcess, _auth_url(), branch_exists(), build_branch_name(), clone_if_missing(), commit_file(), commit_files(), create_task_branch() (+35 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (48): GraphHandle, Immutable reference to a resolved, validated knowledge graph.      Produced excl, GraphConfig, GraphHandle, _build_graph(), _compute_repo_id(), _get_head_sha(), graph_resolver_node() (+40 more)

### Community 10 - "Patch Application"
Cohesion: 0.50
Nodes (3): int, str, main()

### Community 12 - "Simple Repo Fixture"
Cohesion: 0.14
Nodes (24): AppConfig, get_coder_model(), get_coder_model_config(), get_ollama_base_url(), get_primary_model(), get_semantic_model(), get_semantic_model_config(), ModelConfig (+16 more)

### Community 19 - "Community 19"
Cohesion: 0.24
Nodes (10): change_planner_node(), _parse_plan(), Change planner node — produces an ordered, symbol-centric execution plan.  Given, Order files so definition files precede their importers.      Falls back to the, Parse LLM output into a list of valid ChangePlanStep dicts., Create an ordered, symbol-centric execution plan for multi-file changes.      St, _topological_order(), GraphState (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.38
Nodes (6): create_pull_request(), _parse_owner_repo(), GitHub pull request creation via the REST API., Extract (owner, repo) from a GitHub remote URL., Create a GitHub pull request and return its HTML URL.      Args:         remote_, str

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (13): GraphState: original_code field, OllamaClient, file_reader_node(), Read the target file (or select one) and return its contents.      Expected stat, Shared helpers for graph node implementations., Return a required value from `state` or raise ValueError., Pick the first Python file in a repo root deterministically., require_state_value() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.29
Nodes (7): get_semantic_threshold(), float, Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass.

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (23): dependency_analyzer_node(), Dependency analyzer node — expands planner's file selection to all affected file, Expand target_files to all files that may need modification.      State inputs c, plan_dispatcher_node(), Plan dispatcher node — manages iteration over a multi-file execution plan.  Call, Advance to the next step in the execution plan.      State inputs consumed:, Planner node — selects which file(s) to modify from retrieval candidates.  When, emit_event() (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (17): ContextAssembler, Deterministic, capped context assembler that consumes a snapshot.      Returns a, ContextBudget, Allocates ranked files against char and file-count limits.      Limits are adv, Allocates ranked files against char-per-file, file-count, and token limits., AstIndexer, Concrete indexer producing a RepositorySnapshot for a given root., Retrieval node — orchestrates the graph-backed retrieval pipeline.  Pipeline sta (+9 more)

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (11): _build_semantic_feedback(), Semantic validator node.  Evaluates whether the generated code correctly satisfi, Format the LLM evaluation into a concise string for the coder prompt., Format the LLM evaluation into a concise string for the coder prompt., Evaluate task-intent alignment of the generated code using an LLM judge.      Re, Evaluate task-intent alignment and regression risk of the generated change., semantic_validator_node(), float (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (15): ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All run, Create all required runtime directories if they don't exist.      Uses `parents=, Create a fresh RunContext with a new UUID4 run_id., Create a fresh RunContext with a new UUID4 run_id and current timestamp., format_run_console(), log_event(), Minimal JSONL logger and run summary writer for per-run observability events.  P (+7 more)

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (7): GraphStateFactory, Build the initial GraphState from a validated TaskRequest., Converts an external TaskRequest into the internal GraphState.      This is the, External request contract for submitting a task to the workflow.      Separates, TaskRequest, GraphState, TaskRequest

### Community 33 - "Community 33"
Cohesion: 0.08
Nodes (36): GraphState: review_passed field, GraphState: verification_passed field, _exhaustion_target(), make_graph(), Graph construction helpers for the file-edit workflow.  This module builds a `St, Terminate early if the change planner could not produce a valid plan., Decide the next node after a file is written.      - plan_failed → git_committer, Create and compile the StateGraph for a single run.      The returned graph is c (+28 more)

### Community 36 - "Community 36"
Cohesion: 0.20
Nodes (10): Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json. (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.16
Nodes (13): Sandbox Subprocess Execution Pattern, _classify_error(), Return a coarse error category from subprocess output., Verify generated code by executing it in a sandboxed subprocess.      Subprocess, verifier_node(), GraphState, RunContext, str (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.25
Nodes (8): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Bounded Autonomy Design Principle, Mutation Exclusivity - One Active Workflow at a Time, Phase 2 - Repository Awareness, Phase 3 - Async Execution Coordinator

### Community 40 - "Community 40"
Cohesion: 0.19
Nodes (14): GraphState, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a single, build_ast_graph(), graphify_indexer_node(), Graphify indexer — internal graph-building utility.  Provides `build_ast_graph`,, Run AST-only graphify extraction and write graph.json to graph_dir. (+6 more)

### Community 41 - "Community 41"
Cohesion: 0.29
Nodes (6): git_committer_node(), Git committer node.  Stages the modified target file and creates a git commit on, Stage and commit the modified target file.      Expected state keys:     - ``, Stage and commit the modified target file.      Expected state keys:     - ``rep, GraphState, RunContext

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (13): int, get_max_iterations(), get_repository_config(), int, Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no rep (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.27
Nodes (17): Any, Path, load_config(), _load_model_config(), _load_planner_config(), _load_repository_config(), Any, Path (+9 more)

### Community 44 - "Community 44"
Cohesion: 0.29
Nodes (6): WorkflowExecutor as Single Orchestration Boundary, Executor that runs a workflow graph for a given `Task`.      The executor acce, Executor that runs a workflow graph for a given `Task`.      The executor accept, WorkflowExecutor, TaskQueue, WorkflowExecutor

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
Cohesion: 0.29
Nodes (7): GraphState: repository_context field, OllamaClient.chat, coder_node(), _format_related_files(), GraphState, RunContext, str

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (13): _heuristic_rank(), Fallback ranking when graph is unavailable., Fallback ranking when graph is unavailable., Read bounded file contents for the coder prompt, excluding target file., Read bounded file contents for the coder prompt, excluding target file., Convert absolute paths to repo-relative strings when possible., Convert absolute paths to repo-relative strings when possible., Fallback ranking when graph is unavailable. (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (7): _load_graph_config(), Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults to

### Community 52 - "Community 52"
Cohesion: 0.40
Nodes (4): Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool.

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (6): _build_importer_index(), _expand_with_importers(), Return a mapping from each file to the list of files that import it., BFS expansion: return seed_files plus all files that import from them.      Pres, int, str

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (5): Active Mode - User-triggered Code Modification, Passive Mode - Continuous Repository Analysis, Phase 1 - File Mutation MVP, Phase 4 - Passive Analysis System, TaskType (passive|active)

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (7): _load_system_config(), Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~/.

### Community 57 - "Community 57"
Cohesion: 0.10
Nodes (30): Build and return a bounded ContextPackage.          Must be deterministic and mu, build_repository_context_payload(), _dedupe_preserve_order(), DependencySummaryItem, format_repository_context_for_prompt(), _normalize_path(), Versioned contract for retrieval -> coder repository context payloads.  This mod, Validate structural invariants for a repository context payload. (+22 more)

### Community 58 - "Community 58"
Cohesion: 0.16
Nodes (14): branch_creator_node(), Branch creator node.  Creates (or checks out) a task branch in the target reposi, Create a task branch in the target repository.      Reads ``repo_path`` and ``ta, diff_generator_node(), Compute a unified diff between the original and generated code.      Expected st, new(), RunContext helper for observability.  This module provides a minimal `RunContext, Minimal per-run observability context.      Attributes:         run_id: A UUI (+6 more)

### Community 61 - "Community 61"
Cohesion: 0.22
Nodes (8): GraphQuery, Graph query utilities for the retrieval pipeline.  GraphQuery loads graph.json o, Loads graph.json once and exposes keyword + dependency queries.      Constructed, GraphQuery, Graph-aware file ranker.  GraphRanker uses a GraphQuery instance to rank file ca, Return an ordered list of file paths relevant to `task`.          Pipeline:, int, str

## Knowledge Gaps
- **26 isolated node(s):** `float`, `str`, `int`, `str`, `int` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GraphState` connect `Community 40` to `Community 1`, `Design Contracts & Project Plan`, `Community 9`, `Community 19`, `Community 26`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 37`, `Community 41`, `Community 44`, `Community 48`, `Community 49`, `Community 50`, `Community 53`, `Community 57`, `Community 58`?**
  _High betweenness centrality (0.254) - this node is a cross-community bridge._
- **Why does `RunContext` connect `Community 58` to `Community 1`, `Community 33`, `Design Contracts & Project Plan`, `Community 37`, `Community 40`, `Community 9`, `Community 41`, `Community 44`, `Community 48`, `Community 49`, `Community 50`, `Community 19`, `Community 53`, `Community 26`, `Community 28`, `Community 29`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `get_repository_config()` connect `Community 42` to `Community 1`, `Community 33`, `Community 9`, `Community 43`, `Simple Repo Fixture`, `Community 45`, `Community 46`, `Community 50`, `Community 58`, `Community 27`, `Community 31`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Are the 65 inferred relationships involving `GraphState` (e.g. with `RepositoryContextPayload` and `RetrievalResult`) actually correct?**
  _`GraphState` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 59 inferred relationships involving `RunContext` (e.g. with `GraphConfig` and `GraphHandle`) actually correct?**
  _`RunContext` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `emit_success()` (e.g. with `coder_node()` and `file_reader_node()`) actually correct?**
  _`emit_success()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `emit_failure()` (e.g. with `coder_node()` and `file_reader_node()`) actually correct?**
  _`emit_failure()` has 5 INFERRED edges - model-reasoned connections that need verification._