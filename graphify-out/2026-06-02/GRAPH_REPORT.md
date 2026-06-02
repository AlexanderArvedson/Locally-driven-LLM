# Graph Report - Locally-driven-langgraph-LLM  (2026-06-02)

## Corpus Check
- 58 files · ~17,067 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 684 nodes · 1408 edges · 54 communities (39 shown, 15 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 250 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4d86437d`
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
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 61|Community 61]]

## God Nodes (most connected - your core abstractions)
1. `GraphState` - 79 edges
2. `RunContext` - 73 edges
3. `emit_success()` - 35 edges
4. `emit_failure()` - 34 edges
5. `get_repository_config()` - 32 edges
6. `RepositorySnapshot` - 27 edges
7. `str` - 24 edges
8. `require_state_value()` - 24 edges
9. `retrieval_node()` - 19 edges
10. `GraphQuery` - 18 edges

## Surprising Connections (you probably didn't know these)
- `diff_generator_node()` --implements--> `Phase 1 - File Mutation MVP`  [INFERRED]
  src/graph/nodes/diff_generator.py → docs/PROJECT_PLAN.md
- `WorkflowExecutor` --implements--> `WorkflowExecutor as Single Orchestration Boundary`  [INFERRED]
  src/scheduler/executor.py → docs/PROJECT_PLAN.md
- `TaskQueue` --implements--> `FIFO Task Queue - In-memory Deterministic Ordering`  [INFERRED]
  src/scheduler/queue.py → docs/PROJECT_PLAN.md
- `ExecutionLoop` --implements--> `Phase 3 - Async Execution Coordinator`  [INFERRED]
  src/scheduler/loop.py → docs/PROJECT_PLAN.md
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

## Communities (54 total, 15 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.22
Nodes (7): BudgetAllocation, Context window budget allocation.  ContextBudget enforces per-file character lim, Result of a budget allocation pass., Result of a budget allocation pass.      Attributes:         selected_files: Ord, Return the largest prefix of `ranked_files` that fits the budget.          Tar, Return the largest prefix of `ranked_files` that fits within all limits., str

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (18): bool, GraphState: generated_code field, Perform lightweight review checks on generated code.      Performs the following, reviewer_node(), Remove a single pair of surrounding Markdown code fences., Validate that `content` compiles as Python., strip_code_fences(), validate_python_syntax() (+10 more)

### Community 2 - "Repository Context & Graph State"
Cohesion: 0.20
Nodes (12): RepositoryContextPayload, Output contract from the retrieval pipeline, stored in GraphState.      Downstre, RetrievalResult, GraphState, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a single, diff_generator_node() (+4 more)

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.06
Nodes (48): ContextAssemblerProtocol, Context assembler — builds bounded ContextPackage from ranked files.  ContextAss, Interface for bounded context assembly., Build and return a bounded ContextPackage.          Must be deterministic and mu, ContextPackage, DependencyEdge, FileNode, Core data types shared across the retrieval pipeline.  Defines the immutable sna (+40 more)

### Community 4 - "Design Contracts & Project Plan"
Cohesion: 0.50
Nodes (4): Convert absolute paths to repo-relative strings when possible., Convert absolute paths to repo-relative strings when possible., Convert absolute paths to repo-relative strings when possible., _to_relative_ids()

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.14
Nodes (15): _gpu_layers(), LLMResult, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal `, Return the Ollama ``num_gpu`` value for a given ``allow_gpu`` flag.      Ollama, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Send a chat request to the Ollama API and return a parsed result.          The, Create a new `OllamaClient`.          Args:             base_url: Base URL of th (+7 more)

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.15
Nodes (10): Map resolved absolute file paths to their highest node score.          Nodes wit, Like `files_for_nodes` but preserves per-node scores.          Maps each absolut, Extract normalised, non-stopword tokens from a task string., Load graph.json from `graph_dir` and return a GraphQuery instance.          Read, Return (node_id, score) pairs ranked by keyword overlap with task words., BFS expansion: return all node_ids reachable within `hops` edges.          Inclu, float, int (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (39): CompletedProcess, _auth_url(), branch_exists(), build_branch_name(), clone_if_missing(), commit_file(), create_task_branch(), get_diff_stat() (+31 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (47): GraphHandle, Immutable reference to a resolved, validated knowledge graph.      Produced excl, GraphConfig, GraphHandle, _build_graph(), _compute_repo_id(), _get_head_sha(), graph_resolver_node() (+39 more)

### Community 10 - "Patch Application"
Cohesion: 0.50
Nodes (3): int, str, main()

### Community 12 - "Simple Repo Fixture"
Cohesion: 0.17
Nodes (19): AppConfig, get_coder_model(), get_coder_model_config(), get_ollama_base_url(), get_primary_model(), get_semantic_model_config(), ModelConfig, str (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (5): Static validator node.  Replaces the former reviewer node. Responsibilities are, Validate generated code for structural correctness.      Runs Python syntax vali, static_validator_node(), GraphState, RunContext

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
Cohesion: 0.22
Nodes (13): Planner node — selects which file(s) to modify from retrieval candidates.  When, emit_event(), emit_failure(), emit_success(), Small helper utilities for observability event emission.  Provides helpers to em, Emit a single observability event with consistent shape.      Args:         r, Emit a single compact observability event.      Args:         run_context: The R, Emit a success event for the given node. (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.19
Nodes (15): ContextAssembler, Deterministic, capped context assembler that consumes a snapshot.      Returns a, ContextBudget, Allocates ranked files against char and file-count limits.      Limits are adv, Allocates ranked files against char-per-file, file-count, and token limits., Retrieval node — orchestrates the graph-backed retrieval pipeline.  Pipeline sta, Build repository context for the current task and target file.      Retrieval, Build repository context for the current task and target file.      Retrieval st (+7 more)

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (11): _build_semantic_feedback(), Semantic validator node.  Evaluates whether the generated code correctly satisfi, Format the LLM evaluation into a concise string for the coder prompt., Format the LLM evaluation into a concise string for the coder prompt., Evaluate task-intent alignment of the generated code using an LLM judge.      Re, Evaluate task-intent alignment and regression risk of the generated change., semantic_validator_node(), float (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.06
Nodes (46): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Active Mode - User-triggered Code Modification, Bounded Autonomy Design Principle, FIFO Task Queue - In-memory Deterministic Ordering, Mutation Exclusivity - One Active Workflow at a Time (+38 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (26): GraphState: review_passed field, GraphState: verification_passed field, make_graph(), Graph construction helpers for the file-edit workflow.  This module builds a `St, Decide the next graph node after the `reviewer` (static_validator) node.      -, Decide the next graph node after the `verifier` node.      - If verification pas, Decide the next graph node after the `semantic_validator` node.      - If semant, Decide the next graph node after the `semantic_validator` node.      - If semant (+18 more)

### Community 37 - "Community 37"
Cohesion: 0.29
Nodes (6): Sandbox Subprocess Execution Pattern, int, str, Helper API to run untrusted/generated Python code in a subprocess sandbox.  This, Run `code` in a subprocess with limits.      Args:         code: Python source t, run_code_in_sandbox()

### Community 40 - "Community 40"
Cohesion: 0.17
Nodes (15): build_ast_graph(), graphify_indexer_node(), Graphify indexer — internal graph-building utility.  Provides `build_ast_graph`,, Run AST-only graphify extraction and write graph.json to graph_dir., Build or refresh the graphify knowledge graph for the target repository., Run AST-only graphify extraction and write graph.json to graph_dir., new(), RunContext helper for observability.  This module provides a minimal `RunContext (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.29
Nodes (6): git_committer_node(), Git committer node.  Stages the modified target file and creates a git commit on, Stage and commit the modified target file.      Expected state keys:     - ``, Stage and commit the modified target file.      Expected state keys:     - ``rep, GraphState, RunContext

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (10): get_repository_config(), Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no rep, Return the configured repository that best matches `repo_path`.      If no rep (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.27
Nodes (17): Any, Path, load_config(), _load_model_config(), _load_planner_config(), _load_repository_config(), Any, Path (+9 more)

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (14): get_retrieval_config(), _load_retrieval_config(), Parse the ``retrieval`` sub-object from a repository config entry.      All fi, Parse the ``retrieval`` sub-object from a repository config entry.      All fi, Parse the ``retrieval`` sub-object from a repository config entry.      All fi, Parse the ``retrieval`` sub-object from a repository config entry.      All fiel, Return retrieval limits and behavior for the repository matching ``repo_path``., Return retrieval limits and behavior for the repository matching ``repo_path``. (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (11): get_planner_config(), PlannerConfig, Global system-level settings shared across all repositories.      Attributes:, Return planner settings for the repository matching ``repo_path``., Return planner settings for the repository matching ``repo_path``., Global system-level settings shared across all repositories.      Attributes:, Global system-level settings shared across all repositories.      Attributes:, Controls how many files the planner node may select for modification.      Att (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.06
Nodes (42): bytes, ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All run, Create all required runtime directories if they don't exist.      Uses `parents=, file_writer_node(), Write generated content to disk or apply a unified diff.      Expected state inp, Write generated content to disk or apply a unified diff.      Expected state inp, Persist ``created_at`` and/or ``updated_at`` for a repository in config.json. (+34 more)

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (7): GraphState: repository_context field, OllamaClient.chat, coder_node(), _format_related_files(), GraphState, RunContext, str

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (9): _heuristic_rank(), Fallback ranking when graph is unavailable., Fallback ranking when graph is unavailable., Read bounded file contents for the coder prompt, excluding target file., Read bounded file contents for the coder prompt, excluding target file., Fallback ranking when graph is unavailable., Read bounded file contents for the coder prompt, excluding target file., _read_related_files() (+1 more)

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (7): _load_graph_config(), Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults t, Parse the ``graph`` sub-object from a repository config entry.      Defaults to

### Community 52 - "Community 52"
Cohesion: 0.40
Nodes (4): Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool.

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (7): _load_system_config(), Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~, Parse the top-level ``system`` block from config.json.      Falls back to ``"~/.

### Community 57 - "Community 57"
Cohesion: 0.09
Nodes (29): build_repository_context_payload(), _dedupe_preserve_order(), DependencySummaryItem, format_repository_context_for_prompt(), _normalize_path(), Versioned contract for retrieval -> coder repository context payloads.  This mod, Validate structural invariants for a repository context payload., Render repository context in a fixed, deterministic prompt section. (+21 more)

### Community 58 - "Community 58"
Cohesion: 0.25
Nodes (6): branch_creator_node(), Branch creator node.  Creates (or checks out) a task branch in the target reposi, Create a task branch in the target repository.      Reads ``repo_path`` and ``ta, Aggregate export surface for graph nodes., GraphState, RunContext

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (6): get_semantic_model(), Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semanti, Return the model name for the semantic validator.      Prefers models["semantic_

### Community 61 - "Community 61"
Cohesion: 0.22
Nodes (8): GraphQuery, Graph query utilities for the retrieval pipeline.  GraphQuery loads graph.json o, Loads graph.json once and exposes keyword + dependency queries.      Constructed, GraphQuery, Graph-aware file ranker.  GraphRanker uses a GraphQuery instance to rank file ca, Return an ordered list of file paths relevant to `task`.          Pipeline:, int, str

## Knowledge Gaps
- **26 isolated node(s):** `float`, `str`, `int`, `str`, `int` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GraphState` connect `Repository Context & Graph State` to `Community 33`, `Community 1`, `Community 26`, `Community 40`, `Community 9`, `Community 41`, `Community 47`, `Community 48`, `Community 49`, `Community 19`, `Community 57`, `Community 58`, `Community 28`, `Community 29`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Why does `RunContext` connect `Community 40` to `Community 1`, `Repository Context & Graph State`, `Community 26`, `Community 33`, `Community 9`, `Community 41`, `Community 47`, `Community 48`, `Community 49`, `Community 19`, `Community 57`, `Community 58`, `Community 28`, `Community 29`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `get_repository_config()` connect `Community 42` to `Community 33`, `Community 27`, `Community 9`, `Community 43`, `Simple Repo Fixture`, `Community 45`, `Community 46`, `Community 47`, `Community 58`, `Community 59`, `Community 28`, `Community 31`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `GraphState` (e.g. with `RepositoryContextPayload` and `RetrievalResult`) actually correct?**
  _`GraphState` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `RunContext` (e.g. with `GraphConfig` and `GraphHandle`) actually correct?**
  _`RunContext` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `emit_success()` (e.g. with `coder_node()` and `file_reader_node()`) actually correct?**
  _`emit_success()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `emit_failure()` (e.g. with `coder_node()` and `file_reader_node()`) actually correct?**
  _`emit_failure()` has 5 INFERRED edges - model-reasoned connections that need verification._