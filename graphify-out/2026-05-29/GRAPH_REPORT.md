# Graph Report - Locally-driven-langgraph-LLM  (2026-05-29)

## Corpus Check
- 52 files · ~11,762 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 480 nodes · 1038 edges · 30 communities (16 shown, 14 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 213 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5f285401`
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
- [[_COMMUNITY_Node Index|Node Index]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Repository Package Init|Repository Package Init]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Runtime Directory|Runtime Directory]]
- [[_COMMUNITY_Phase 5 Advanced Maintenance|Phase 5 Advanced Maintenance]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]

## God Nodes (most connected - your core abstractions)
1. `GraphState` - 60 edges
2. `RunContext` - 59 edges
3. `emit_success()` - 28 edges
4. `emit_failure()` - 27 edges
5. `RepositorySnapshot` - 27 edges
6. `get_repository_config()` - 20 edges
7. `require_state_value()` - 20 edges
8. `GraphQuery` - 18 edges
9. `file_writer_node()` - 17 edges
10. `ContextPackage` - 16 edges

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

## Communities (30 total, 14 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.29
Nodes (7): GraphState: review_passed field, GraphState: verification_passed field, Decide the next graph node after the `reviewer` node.      - If the review pas, Decide the next graph node after the `verifier` node.      - If verification p, route_after_review(), route_after_verification(), GraphState

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (89): bool, GraphState: generated_code field, GraphState: original_code field, GraphState: repository_context field, OllamaClient.chat, OllamaClient, Close the underlying HTTP client connection pool., GraphState (+81 more)

### Community 2 - "Repository Context & Graph State"
Cohesion: 0.13
Nodes (24): Build and return a bounded ContextPackage.          Must be deterministic and mu, build_repository_context_payload(), _dedupe_preserve_order(), DependencySummaryItem, format_repository_context_for_prompt(), _normalize_path(), Versioned contract for retrieval -> coder repository context payloads.  This mod, Validate structural invariants for a repository context payload. (+16 more)

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.07
Nodes (41): ContextAssemblerProtocol, Context assembler — builds bounded ContextPackage from ranked files.  ContextAss, Interface for bounded context assembly., DependencyEdge, FileNode, Core data types shared across the retrieval pipeline.  Defines the immutable sna, Represents a top-level symbol extracted from a file., Represents a directed import relationship between files. (+33 more)

### Community 4 - "Design Contracts & Project Plan"
Cohesion: 0.08
Nodes (28): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Active Mode - User-triggered Code Modification, Bounded Autonomy Design Principle, FIFO Task Queue - In-memory Deterministic Ordering, Mutation Exclusivity - One Active Workflow at a Time (+20 more)

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.25
Nodes (6): LLMResult, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal, Create a new `OllamaClient`.          Args:             base_url: Base URL of, Send a chat request to the Ollama API and return a parsed result.          The, float, str

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.06
Nodes (45): ContextAssembler, Deterministic, capped context assembler that consumes a snapshot.      Returns a, BudgetAllocation, ContextBudget, Context window budget allocation.  ContextBudget enforces per-file and total cha, Result of a budget allocation pass., Allocates ranked files against char and file-count limits.      Limits are advis, Return the largest prefix of `ranked_files` that fits the budget.          Targe (+37 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (30): CompletedProcess, _auth_url(), branch_exists(), build_branch_name(), clone_if_missing(), commit_file(), create_task_branch(), _open_repo() (+22 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (35): GraphHandle, Immutable reference to a resolved, validated knowledge graph.      Produced ex, GraphConfig, GraphHandle, _build_graph(), _compute_repo_id(), _get_head_sha(), graph_resolver_node() (+27 more)

### Community 10 - "Patch Application"
Cohesion: 0.32
Nodes (7): str, apply_ndiff(), apply_unified(), generate_ndiff(), Return an ndiff-formatted string describing changes from original -> modified., Apply an ndiff string to reconstruct the modified file and write it to path., Apply a unified diff to the file at `path`.      This is a lightweight unified

### Community 12 - "Simple Repo Fixture"
Cohesion: 0.13
Nodes (39): Any, int, Path, AppConfig, get_coder_model(), get_graph_config(), get_max_iterations(), get_ollama_base_url() (+31 more)

### Community 19 - "Node Index"
Cohesion: 0.25
Nodes (7): ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All r, Create all required runtime directories if they don't exist.      Uses `parent, log_event(), Minimal JSONL logger for per-run observability events.  Provides one simple fu, Append `event` as one JSON line to the per-run JSONL file.      Writes directl, str

### Community 20 - "Community 20"
Cohesion: 0.38
Nodes (6): create_pull_request(), _parse_owner_repo(), GitHub pull request creation via the REST API., Extract (owner, repo) from a GitHub remote URL., Create a GitHub pull request and return its HTML URL.      Args:         remote_, str

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (9): Sandbox Subprocess Execution Pattern, int, str, int, str, Helper API to run untrusted/generated Python code in a subprocess sandbox.  Th, Run `code` in a subprocess with limits.      Args:         code: Python sourc, run_code_in_sandbox() (+1 more)

## Knowledge Gaps
- **26 isolated node(s):** `bool`, `str`, `int`, `str`, `str` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GraphState` connect `Community 1` to `Graph State Data Flow`, `Repository Context & Graph State`, `Design Contracts & Project Plan`, `Repository Indexer Protocol`, `Community 9`?**
  _High betweenness centrality (0.261) - this node is a cross-community bridge._
- **Why does `RunContext` connect `Community 1` to `Graph State Data Flow`, `Community 9`, `Design Contracts & Project Plan`, `Repository Indexer Protocol`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Why does `RepositorySnapshot` connect `Test Infrastructure & Fixtures` to `Repository Context & Graph State`, `Repository Indexer Protocol`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `GraphState` (e.g. with `RepositoryContextPayload` and `GraphHandle`) actually correct?**
  _`GraphState` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `RunContext` (e.g. with `GraphConfig` and `GraphHandle`) actually correct?**
  _`RunContext` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `emit_success()` (e.g. with `coder_node()` and `file_reader_node()`) actually correct?**
  _`emit_success()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `emit_failure()` (e.g. with `coder_node()` and `file_reader_node()`) actually correct?**
  _`emit_failure()` has 5 INFERRED edges - model-reasoned connections that need verification._