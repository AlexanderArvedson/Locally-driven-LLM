# Graph Report - Locally-driven-langgraph-LLM  (2026-05-29)

## Corpus Check
- 40 files · ~8,807 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 361 nodes · 818 edges · 30 communities (22 shown, 8 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 189 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e0849cbc`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Graph State Data Flow|Graph State Data Flow]]
- [[_COMMUNITY_Fixture App & Legacy Adapter|Fixture App & Legacy Adapter]]
- [[_COMMUNITY_Repository Context & Graph State|Repository Context & Graph State]]
- [[_COMMUNITY_Test Infrastructure & Fixtures|Test Infrastructure & Fixtures]]
- [[_COMMUNITY_Design Contracts & Project Plan|Design Contracts & Project Plan]]
- [[_COMMUNITY_LLM Pipeline & Sandbox|LLM Pipeline & Sandbox]]
- [[_COMMUNITY_Repository Indexer Protocol|Repository Indexer Protocol]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Scheduler Entry & Execution Loop|Scheduler Entry & Execution Loop]]
- [[_COMMUNITY_Stress Testing Scripts|Stress Testing Scripts]]
- [[_COMMUNITY_Patch Application|Patch Application]]
- [[_COMMUNITY_Fixture Mutation Scripts|Fixture Mutation Scripts]]
- [[_COMMUNITY_Simple Repo Fixture|Simple Repo Fixture]]
- [[_COMMUNITY_Repo Config Schema|Repo Config Schema]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Infrastructure & Docs|Infrastructure & Docs]]
- [[_COMMUNITY_Sample Repo v2 Docs|Sample Repo v2 Docs]]
- [[_COMMUNITY_Node Package Init|Node Package Init]]
- [[_COMMUNITY_Node Index|Node Index]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Repository Package Init|Repository Package Init]]
- [[_COMMUNITY_Repository Snapshot Builder|Repository Snapshot Builder]]
- [[_COMMUNITY_Runtime Directory|Runtime Directory]]
- [[_COMMUNITY_Phase 5 Advanced Maintenance|Phase 5 Advanced Maintenance]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]

## God Nodes (most connected - your core abstractions)
1. `RunContext` - 50 edges
2. `GraphState` - 49 edges
3. `RepositorySnapshot` - 32 edges
4. `emit_success()` - 24 edges
5. `emit_failure()` - 23 edges
6. `context_builder_node()` - 20 edges
7. `require_state_value()` - 18 edges
8. `ContextPackage` - 18 edges
9. `file_writer_node()` - 17 edges
10. `SimpleRepositoryIndexer` - 17 edges

## Surprising Connections (you probably didn't know these)
- `diff_generator_node()` --implements--> `Phase 1 - File Mutation MVP`  [INFERRED]
  src/graph/nodes/diff_generator.py → docs/PROJECT_PLAN.md
- `WorkflowExecutor` --implements--> `WorkflowExecutor as Single Orchestration Boundary`  [INFERRED]
  src/scheduler/executor.py → docs/PROJECT_PLAN.md
- `ExecutionLoop` --implements--> `Phase 3 - Async Execution Coordinator`  [INFERRED]
  src/scheduler/loop.py → docs/PROJECT_PLAN.md
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

## Communities (30 total, 8 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.16
Nodes (15): bool, GraphState: generated_code field, Perform lightweight review checks on generated code.      Performs the followi, reviewer_node(), Remove a single pair of surrounding Markdown code fences., Validate that `content` compiles as Python., strip_code_fences(), validate_python_syntax() (+7 more)

### Community 1 - "Fixture App & Legacy Adapter"
Cohesion: 0.21
Nodes (14): branch_creator_node(), Branch creator node.  Creates (or checks out) a task branch in the target reposi, Create a task branch in the target repository.      Reads ``repo_path`` and ``ta, emit_event(), emit_failure(), emit_success(), Small helper utilities for observability event emission.  Provides helpers to, Emit a single observability event with consistent shape.      Args:         r (+6 more)

### Community 2 - "Repository Context & Graph State"
Cohesion: 0.11
Nodes (28): SimpleContextBuilder.build_context, ContextBuilder, Context builder interface and a simple deterministic implementation.  The Cont, Interface for bounded context assembly., Build and return a bounded ContextPackage.          The implementation must be, build_repository_context_payload(), _dedupe_preserve_order(), DependencySummaryItem (+20 more)

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.13
Nodes (26): DependencyEdge, Repository indexer interfaces.  Skeleton only: no indexing logic yet., Interface for repository indexing.      The indexer builds an immutable `Repos, Build and return an immutable repository snapshot for `root_path`., Return symbol names for a given file from the snapshot., Return dependency target paths for a given file from the snapshot., RepositoryIndexer, DependencyEdge (+18 more)

### Community 4 - "Design Contracts & Project Plan"
Cohesion: 0.10
Nodes (23): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Bounded Autonomy Design Principle, FIFO Task Queue - In-memory Deterministic Ordering, Mutation Exclusivity - One Active Workflow at a Time, Phase 2 - Repository Awareness (+15 more)

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.25
Nodes (6): LLMResult, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Send a chat request to the Ollama API and return a parsed result.          The, float, str

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.08
Nodes (34): GraphState: repository_snapshot field, context_builder_node(), Repository context builder node., Select files from the graphify graph most relevant to the task.      Scores gr, Build repository context for the current task and target file.      Expected sta, Build repository context for the current task and target file.      When `grap, Read the contents of selected related files, excluding the target file.      C, _read_related_files() (+26 more)

### Community 7 - "Community 7"
Cohesion: 0.21
Nodes (16): CompletedProcess, branch_exists(), build_branch_name(), create_task_branch(), push_branch(), Git branch management for target repositories.  Provides utilities to create tas, Convert a free-text task description into a safe branch-name segment., Return the full branch name: ``<prefix><sanitized-task>``. (+8 more)

### Community 8 - "Scheduler Entry & Execution Loop"
Cohesion: 0.26
Nodes (11): GraphState, Shared state passed between LangGraph nodes.      This state represents a sing, _build_ast_graph(), graphify_indexer_node(), Graphify indexer node — builds a knowledge graph of the target repository.  Ru, Build or refresh the graphify knowledge graph for the target repository., Run AST-only graphify extraction and write graph.json to graph_dir., GraphState (+3 more)

### Community 9 - "Stress Testing Scripts"
Cohesion: 0.24
Nodes (10): diff_generator_node(), Compute a unified diff between the original and generated code.      Expected, new(), RunContext helper for observability.  This module provides a minimal `RunConte, Minimal per-run observability context.      Attributes:         run_id: A UUI, RunContext, GraphState, RunContext (+2 more)

### Community 10 - "Patch Application"
Cohesion: 0.32
Nodes (7): str, apply_ndiff(), apply_unified(), generate_ndiff(), Return an ndiff-formatted string describing changes from original -> modified., Apply an ndiff string to reconstruct the modified file and write it to path., Apply a unified diff to the file at `path`.      This is a lightweight unified

### Community 11 - "Fixture Mutation Scripts"
Cohesion: 0.20
Nodes (9): make_graph(), Create and compile the StateGraph for a single run.      The returned graph is, file_writer_node(), Write generated content to disk or apply a unified diff.      Expected state inp, Write generated content to disk or apply a unified diff.      Expected state i, Aggregate export surface for graph nodes., GraphState, RunContext (+1 more)

### Community 12 - "Simple Repo Fixture"
Cohesion: 0.21
Nodes (27): Any, int, Path, AppConfig, get_coder_model(), get_max_iterations(), get_ollama_base_url(), get_primary_model() (+19 more)

### Community 13 - "Repo Config Schema"
Cohesion: 0.16
Nodes (14): GraphState: original_code field, OllamaClient, Close the underlying HTTP client connection pool., file_reader_node(), Read the target file (or select one) and return its contents.      Expected st, Shared helpers for graph node implementations., Return a required value from `state` or raise ValueError., Pick the first Python file in a repo root deterministically. (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (8): GraphState: review_passed field, GraphState: verification_passed field, Graph construction helpers for the file-edit workflow.  This module builds a `, Decide the next graph node after the `reviewer` node.      - If the review pas, Decide the next graph node after the `verifier` node.      - If verification p, route_after_review(), route_after_verification(), GraphState

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (7): GraphState: repository_context field, OllamaClient.chat, coder_node(), _format_related_files(), GraphState, RunContext, str

### Community 19 - "Node Index"
Cohesion: 0.25
Nodes (7): ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All r, Create all required runtime directories if they don't exist.      Uses `parent, log_event(), Minimal JSONL logger for per-run observability events.  Provides one simple fu, Append `event` as one JSON line to the per-run JSONL file.      Writes directl, str

### Community 20 - "Community 20"
Cohesion: 0.38
Nodes (6): create_pull_request(), _parse_owner_repo(), GitHub pull request creation via the REST API., Extract (owner, repo) from a GitHub remote URL., Create a GitHub pull request and return its HTML URL.      Args:         remote_, str

### Community 21 - "Community 21"
Cohesion: 0.40
Nodes (5): Active Mode - User-triggered Code Modification, Passive Mode - Continuous Repository Analysis, Phase 1 - File Mutation MVP, Phase 4 - Passive Analysis System, TaskType (passive|active)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (9): Sandbox Subprocess Execution Pattern, int, str, int, str, Helper API to run untrusted/generated Python code in a subprocess sandbox.  Th, Run `code` in a subprocess with limits.      Args:         code: Python sourc, run_code_in_sandbox() (+1 more)

## Knowledge Gaps
- **25 isolated node(s):** `CompletedProcess`, `bool`, `str`, `str`, `str` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GraphState` connect `Scheduler Entry & Execution Loop` to `Graph State Data Flow`, `Fixture App & Legacy Adapter`, `Repository Context & Graph State`, `Test Infrastructure & Fixtures`, `Design Contracts & Project Plan`, `Repository Indexer Protocol`, `Stress Testing Scripts`, `Fixture Mutation Scripts`, `Repo Config Schema`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.344) - this node is a cross-community bridge._
- **Why does `RepositorySnapshot` connect `Test Infrastructure & Fixtures` to `Scheduler Entry & Execution Loop`, `Repository Context & Graph State`, `Repository Indexer Protocol`?**
  _High betweenness centrality (0.212) - this node is a cross-community bridge._
- **Why does `RunContext` connect `Stress Testing Scripts` to `Graph State Data Flow`, `Fixture App & Legacy Adapter`, `Design Contracts & Project Plan`, `Repository Indexer Protocol`, `Scheduler Entry & Execution Loop`, `Fixture Mutation Scripts`, `Repo Config Schema`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `RunContext` (e.g. with `WorkflowExecutor` and `GraphState`) actually correct?**
  _`RunContext` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `GraphState` (e.g. with `RepositoryContextPayload` and `RepositorySnapshot`) actually correct?**
  _`GraphState` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `RepositorySnapshot` (e.g. with `DependencyEdge` and `GraphState`) actually correct?**
  _`RepositorySnapshot` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `emit_success()` (e.g. with `coder_node()` and `context_builder_node()`) actually correct?**
  _`emit_success()` has 6 INFERRED edges - model-reasoned connections that need verification._