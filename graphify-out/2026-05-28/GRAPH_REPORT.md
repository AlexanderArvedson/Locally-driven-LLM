# Graph Report - .  (2026-05-28)

## Corpus Check
- Corpus is ~15,488 words - fits in a single context window. You may not need a graph.

## Summary
- 424 nodes · 668 edges · 36 communities (19 shown, 17 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 177 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Graph State Data Flow|Graph State Data Flow]]
- [[_COMMUNITY_Fixture App & Legacy Adapter|Fixture App & Legacy Adapter]]
- [[_COMMUNITY_Repository Context & Graph State|Repository Context & Graph State]]
- [[_COMMUNITY_Test Infrastructure & Fixtures|Test Infrastructure & Fixtures]]
- [[_COMMUNITY_Design Contracts & Project Plan|Design Contracts & Project Plan]]
- [[_COMMUNITY_LLM Pipeline & Sandbox|LLM Pipeline & Sandbox]]
- [[_COMMUNITY_Repository Indexer Protocol|Repository Indexer Protocol]]
- [[_COMMUNITY_Observability & CI|Observability & CI]]
- [[_COMMUNITY_Scheduler Entry & Execution Loop|Scheduler Entry & Execution Loop]]
- [[_COMMUNITY_Stress Testing Scripts|Stress Testing Scripts]]
- [[_COMMUNITY_Patch Application|Patch Application]]
- [[_COMMUNITY_Fixture Mutation Scripts|Fixture Mutation Scripts]]
- [[_COMMUNITY_Simple Repo Fixture|Simple Repo Fixture]]
- [[_COMMUNITY_Repo Config Schema|Repo Config Schema]]
- [[_COMMUNITY_Dead Legacy Code|Dead Legacy Code]]
- [[_COMMUNITY_Scheduler Stress Runner|Scheduler Stress Runner]]
- [[_COMMUNITY_Infrastructure & Docs|Infrastructure & Docs]]
- [[_COMMUNITY_Sample Repo v2 Docs|Sample Repo v2 Docs]]
- [[_COMMUNITY_Node Package Init|Node Package Init]]
- [[_COMMUNITY_Node Index|Node Index]]
- [[_COMMUNITY_Config Constants|Config Constants]]
- [[_COMMUNITY_Repository Package Init|Repository Package Init]]
- [[_COMMUNITY_Test Package Init|Test Package Init]]
- [[_COMMUNITY_Root Main Entry|Root Main Entry]]
- [[_COMMUNITY_Context Contract Test|Context Contract Test]]
- [[_COMMUNITY_Smoke Runner|Smoke Runner]]
- [[_COMMUNITY_Max Iterations Config|Max Iterations Config]]
- [[_COMMUNITY_Repository Snapshot Builder|Repository Snapshot Builder]]
- [[_COMMUNITY_Runtime Directory|Runtime Directory]]
- [[_COMMUNITY_Phase 5 Advanced Maintenance|Phase 5 Advanced Maintenance]]

## God Nodes (most connected - your core abstractions)
1. `SimpleRepositoryIndexer` - 24 edges
2. `ExecutionLoop` - 17 edges
3. `RecordingWorkflowExecutor` - 16 edges
4. `make_graph()` - 16 edges
5. `SimpleRetrievalEngine` - 14 edges
6. `context_builder_node()` - 14 edges
7. `TestRetrievalIntegration` - 13 edges
8. `RepositorySnapshot` - 13 edges
9. `ContextPackage` - 13 edges
10. `verifier_node()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `diff_generator_node()` --implements--> `Phase 1 - File Mutation MVP`  [INFERRED]
  src/graph/nodes/diff_generator.py → docs/PROJECT_PLAN.md
- `TaskQueue` --implements--> `FIFO Task Queue - In-memory Deterministic Ordering`  [INFERRED]
  src/scheduler/queue.py → docs/PROJECT_PLAN.md
- `ExecutionLoop` --implements--> `Phase 3 - Async Execution Coordinator`  [INFERRED]
  src/scheduler/loop.py → docs/PROJECT_PLAN.md
- `WorkflowExecutor` --implements--> `WorkflowExecutor as Single Orchestration Boundary`  [INFERRED]
  src/scheduler/executor.py → docs/PROJECT_PLAN.md
- `log_event()` --implements--> `Per-run JSONL Observability Traces`  [INFERRED]
  src/observability/logger.py → README.md

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

## Communities (36 total, 17 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.06
Nodes (46): GraphState: generated_code field, GraphState: original_code field, GraphState: repository_context field, GraphState: repository_snapshot field, GraphState: review_passed field, GraphState: verification_passed field, OllamaClient.chat, make_graph() (+38 more)

### Community 1 - "Fixture App & Legacy Adapter"
Cohesion: 0.07
Nodes (26): build_parser(), _load_payloads(), main(), LegacyTaskAdapter, normalize_task(), normalize_task_record_legacy(), TaskReport, Task (+18 more)

### Community 2 - "Repository Context & Graph State"
Cohesion: 0.06
Nodes (38): GraphState, Shared state passed between LangGraph nodes.      This state represents a single, SimpleContextBuilder.build_context, ContextBuilder, Context builder interface and a simple deterministic implementation.  The Contex, Interface for bounded context assembly., Build and return a bounded ContextPackage.          The implementation must be d, Deterministic, capped context builder that consumes a snapshot.      It returns (+30 more)

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.07
Nodes (24): CI Mocking Strategy: monkeypatch OllamaClient + httpx_stub, Retrieval Pipeline: index → select_files → build_context → context payload, LegacyTaskAdapter, sample_repo_v2 main(), load_seed_payloads(), run_task_pipeline(), A deterministic, heuristic-based retrieval engine.       Ordering rules (determi, SimpleRetrievalEngine (+16 more)

### Community 4 - "Design Contracts & Project Plan"
Cohesion: 0.07
Nodes (26): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Active Mode - User-triggered Code Modification, Bounded Autonomy Design Principle, FIFO Task Queue - In-memory Deterministic Ordering, Mutation Exclusivity - One Active Workflow at a Time (+18 more)

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.06
Nodes (25): LangGraph-style pipeline: file_reader → coder → diff_generator → reviewer → verifier → file_writer, Sandbox Subprocess Execution Pattern, LLMResult, OllamaClient, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal `, Create a new `OllamaClient`.          Args:             base_url: Base URL of th, Send a chat request to the Ollama API and return a parsed result.          The m, Close the underlying HTTP client connection pool. (+17 more)

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.10
Nodes (14): Protocol, Repository indexer interfaces.  Skeleton only: no indexing logic yet., Interface for repository indexing.      The indexer builds an immutable `Reposit, Build and return an immutable repository snapshot for `root_path`., Return symbol names for a given file from the snapshot., Return dependency target paths for a given file from the snapshot., RepositoryIndexer, _is_test_path() (+6 more)

### Community 7 - "Observability & CI"
Cohesion: 0.11
Nodes (14): ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All run, Create all required runtime directories if they don't exist.      Uses `parents=, Per-run JSONL Observability Traces, CI GitHub Actions Workflow, CI Runtime Validation Job, log_event(), Minimal JSONL logger for per-run observability events.  Provides one simple func (+6 more)

### Community 8 - "Scheduler Entry & Execution Loop"
Cohesion: 0.21
Nodes (12): ExecutionLoop – FIFO active/passive task scheduling, make_task(), RecordingWorkflowExecutor, test_active_tasks_execute_strictly_in_submission_order, test_active_tasks_execute_strictly_in_submission_order(), test_concurrent_submissions_do_not_drop_or_duplicate_tasks(), test_mutation_exclusivity_never_exceeds_one_active_task, test_mutation_exclusivity_never_exceeds_one_active_task() (+4 more)

### Community 9 - "Stress Testing Scripts"
Cohesion: 0.24
Nodes (9): build_parser(), main(), _make_task(), ObservingWorkflowExecutor, _prepare_working_repo(), Stress the scheduler with multiple mutation tasks against one fixture file.  Thi, _resolve_path(), _run() (+1 more)

### Community 10 - "Patch Application"
Cohesion: 0.18
Nodes (9): TestPatches, apply_ndiff(), apply_unified(), generate_ndiff(), generate_unified(), Return an ndiff-formatted string describing changes from original -> modified., Apply an ndiff string to reconstruct the modified file and write it to path., Return a unified diff string describing changes from original -> modified. (+1 more)

### Community 11 - "Fixture Mutation Scripts"
Cohesion: 0.53
Nodes (5): build_parser(), main(), Run the workflow against the synthetic fixture repository and write the change i, _resolve_path(), _run()

### Community 15 - "Scheduler Stress Runner"
Cohesion: 0.67
Nodes (3): stress_scheduler.main, ObservingWorkflowExecutor, stress_scheduler._run

## Knowledge Gaps
- **29 isolated node(s):** `cron`, `repositories`, `main.py (entry point)`, `test_active_tasks_execute_strictly_in_submission_order`, `test_mutation_exclusivity_never_exceeds_one_active_task` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorkflowExecutor` connect `Design Contracts & Project Plan` to `Scheduler Entry & Execution Loop`, `Stress Testing Scripts`, `Repository Context & Graph State`, `LLM Pipeline & Sandbox`?**
  _High betweenness centrality (0.369) - this node is a cross-community bridge._
- **Why does `GraphState` connect `Repository Context & Graph State` to `Graph State Data Flow`, `Design Contracts & Project Plan`?**
  _High betweenness centrality (0.213) - this node is a cross-community bridge._
- **Why does `RunContext` connect `LLM Pipeline & Sandbox` to `Graph State Data Flow`, `Repository Context & Graph State`, `Test Infrastructure & Fixtures`, `Design Contracts & Project Plan`?**
  _High betweenness centrality (0.203) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `SimpleRepositoryIndexer` (e.g. with `TestRetrievalEngine` and `TestContextBuilderNode`) actually correct?**
  _`SimpleRepositoryIndexer` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `ExecutionLoop` (e.g. with `RecordingWorkflowExecutor` and `ObservingWorkflowExecutor`) actually correct?**
  _`ExecutionLoop` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `RecordingWorkflowExecutor` (e.g. with `WorkflowExecutor` and `ExecutionLoop`) actually correct?**
  _`RecordingWorkflowExecutor` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `make_graph()` (e.g. with `._run_graph_once()` and `._run_graph_once_for_fixture()`) actually correct?**
  _`make_graph()` has 6 INFERRED edges - model-reasoned connections that need verification._