# Graph Report - Locally-driven-langgraph-LLM  (2026-06-11)

## Corpus Check
- 95 files · ~35,843 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1375 nodes · 2944 edges · 97 communities (81 shown, 16 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 667 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `41eb1897`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Graph State Data Flow|Graph State Data Flow]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Test Infrastructure & Fixtures|Test Infrastructure & Fixtures]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_LLM Pipeline & Sandbox|LLM Pipeline & Sandbox]]
- [[_COMMUNITY_Repository Indexer Protocol|Repository Indexer Protocol]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
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
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]

## God Nodes (most connected - your core abstractions)
1. `GraphState` - 74 edges
2. `RunContext` - 69 edges
3. `PipelineConfig` - 63 edges
4. `Neo4jStore` - 61 edges
5. `OllamaClient` - 48 edges
6. `ReporterConfig` - 47 edges
7. `SlackNotifier` - 46 edges
8. `FunctionRecord` - 44 edges
9. `PipelineResult` - 38 edges
10. `SlackPipelineConfig` - 35 edges

## Surprising Connections (you probably didn't know these)
- `diff_generator_node()` --implements--> `Phase 1 - File Mutation MVP`  [INFERRED]
  src/graph/nodes/diff_generator.py → docs/PROJECT_PLAN.md
- `TaskQueue` --implements--> `FIFO Task Queue - In-memory Deterministic Ordering`  [INFERRED]
  src/scheduler/queue.py → docs/PROJECT_PLAN.md
- `WorkflowExecutor` --implements--> `WorkflowExecutor as Single Orchestration Boundary`  [INFERRED]
  src/scheduler/executor.py → docs/PROJECT_PLAN.md
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

## Communities (97 total, 16 thin omitted)

### Community 0 - "Graph State Data Flow"
Cohesion: 0.23
Nodes (20): load_config(), _load_graph_config(), _load_model_config(), _load_planner_config(), _load_repository_config(), _load_retrieval_config(), _raise_invalid_field(), Parse a single model role entry from config, validating inference fields. (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (55): LanguageSlicer, Node, Parser, Symbol-level context slicing for language-agnostic code extraction., LanguageSlicer, Language-agnostic slicing Protocol.  Defines the shared contract that every lang, Everything extracted about one symbol from a source file., Extract and stitch back a named symbol within a source file. (+47 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (29): OllamaClient, Neo4jStore, Async Neo4j driver wrapper for Function nodes and SIMILAR_TO edges., Async Neo4j driver wrapper for Function nodes and SIMILAR_TO edges., PipelineConfig, EmbeddingPipeline, Orchestrates all pipeline stages for a single repository., Orchestrates all pipeline stages for a single repository. (+21 more)

### Community 3 - "Test Infrastructure & Fixtures"
Cohesion: 0.05
Nodes (58): load_pipeline_config(), Pipeline configuration loader.  Reads the top-level ``neo4j`` block and the per-, Load pipeline configuration for a repository.      Args:         config_path: Pa, Load pipeline configuration for a repository.      Args:         config_path: Pa, Load pipeline configuration for a repository.      Args:         config_path: Pa, Load pipeline configuration for a repository.      Args:         config_path: Pa, Load pipeline configuration for a repository.      Args:         config_path: Pa, Load pipeline configuration for a repository.      Args:         config_path: Pa (+50 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (26): create_app(), _make_signature_verifier(), FastAPI application.  Provides a health check endpoint. Slack slash commands are, Create and return the FastAPI application., Return a FastAPI dependency that validates X-Slack-Signature on every request., Create and return the FastAPI application.      Args:         queue: The shared, _parse_pipeline_args(), Slack Socket Mode integration.  Opens a persistent WebSocket connection to Slack (+18 more)

### Community 5 - "LLM Pipeline & Sandbox"
Cohesion: 0.12
Nodes (19): EmbedResult, _gpu_layers(), LLMResult, Thin async client wrapper for Ollama HTTP API.  This module provides a minimal `, Send an embedding request to the Ollama API and return the vector.          Args, Send an embedding request to the Ollama API and return the vector.          Args, Return the Ollama ``num_gpu`` value for a given ``allow_gpu`` flag.      Ollama, Create a new `OllamaClient`.          Args:             base_url: Base URL of (+11 more)

### Community 6 - "Repository Indexer Protocol"
Cohesion: 0.11
Nodes (18): GraphQuery, Graph query utilities for the retrieval pipeline.  GraphQuery loads graph.json o, Map resolved absolute file paths to their highest node score.          Nodes wit, Like `files_for_nodes` but preserves per-node scores.          Maps each absolut, Extract normalised, non-stopword tokens from a task string., Loads graph.json once and exposes keyword + dependency queries.      Constructed, Load graph.json from `graph_dir` and return a GraphQuery instance.          Read, Return (node_id, score) pairs ranked by keyword overlap with task words. (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (56): CompletedProcess, _auth_url(), branch_exists(), build_branch_name(), clone_if_missing(), commit_file(), create_task_branch(), ensure_repo_synced() (+48 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (46): Output contract from the retrieval pipeline, stored in GraphState.      Downstre, Input contract passed from the scheduler layer to the retrieval pipeline., RetrievalRequest, RetrievalResult, get_graph_config(), get_system_context_path(), GraphConfig, Return the graph lifecycle config for the repository matching ``repo_path``. (+38 more)

### Community 10 - "Community 10"
Cohesion: 0.14
Nodes (23): Markdown section renderers for the pipeline report.  Re-exports all render_* fun, Markdown renderers for graph topology and similarity sections.  Covers: Graph Ov, Section 6 — top N most similar function pairs., Section 6 — top N most similar function pairs., Section 7 — top N most connected functions with intra/inter breakdown., Section 7 — top N most connected functions with intra/inter breakdown., Section 8 — top N files by total edge count., Section 8 — top N files by total edge count. (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (22): DescriptionService, _extract_json(), Description service for LLM-generated function summaries.  Wraps ``OllamaClient., Generate descriptions for all records in-place, respecting concurrency limit., Strip code fences and extract the outermost JSON object from the response., Strip code fences and extract the outermost JSON object from the response., Generates structured JSON descriptions of functions via OllamaClient., Generates structured JSON descriptions of functions via OllamaClient. (+14 more)

### Community 19 - "Community 19"
Cohesion: 0.15
Nodes (13): CheckpointConfig, CheckpointManager, make_run_key(), Mid-run checkpoint persistence for the pipeline.  Saves expensive per-record fie, Derive a stable key for this set of changed records.      The key is the first 1, Persists and restores mid-run pipeline state to a local JSON file., Return saved record fields keyed by record ID, or {} if missing/stale/corrupt., Atomically write the expensive fields of all records to disk. (+5 more)

### Community 20 - "Community 20"
Cohesion: 0.38
Nodes (6): create_pull_request(), _parse_owner_repo(), GitHub pull request creation via the REST API., Extract (owner, repo) from a GitHub remote URL., Create a GitHub pull request and return its HTML URL.      Args:         remote_, str

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (28): ContextAssembler, Deterministic, capped context assembler that consumes a snapshot.      Returns a, ContextBudget, Allocates ranked files against char and file-count limits.      Limits are adv, Allocates ranked files against char-per-file, file-count, and token limits., _heuristic_rank(), Retrieval node — orchestrates the graph-backed retrieval pipeline.  Pipeline sta, Fallback ranking when graph is unavailable. (+20 more)

### Community 27 - "Community 27"
Cohesion: 0.22
Nodes (7): Create vector indexes once the embedding dimension is known., Create vector indexes once the embedding dimension is known., Create vector indexes once the embedding dimension is known., Batch-upsert Function nodes using UNWIND for efficiency., Batch-upsert Function nodes using UNWIND for efficiency., Batch-upsert Function nodes using UNWIND for efficiency., FunctionRecord

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (26): branch_creator_node(), Branch creator node.  Creates (or checks out) a task branch in the target reposi, Create a task branch in the target repository.      Reads ``repo_path`` and ``ta, Git committer node.  Stages the modified target file and creates a git commit on, Graphify indexer — internal graph-building utility.  Provides `build_ast_graph`,, Semantic validator node.  Evaluates whether the generated code correctly satisfi, Static validator node.  Replaces the former reviewer node. Responsibilities are, new() (+18 more)

### Community 29 - "Community 29"
Cohesion: 0.22
Nodes (16): GraphState: repository_context field, format_repository_context_for_prompt(), Render repository context in a fixed, deterministic prompt section., OllamaClient.chat, _build_full_file_prompt(), _build_symbol_prompt(), coder_node(), _deindent() (+8 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (17): ContextAssemblerProtocol, Context assembler — builds bounded ContextPackage from ranked files.  ContextAss, Interface for bounded context assembly., Build and return a bounded ContextPackage.          Must be deterministic and mu, ContextPackage, Immutable snapshot of the repository used for deterministic retrieval., Bounded context package returned by the ContextAssembler.      Contains only lig, RepositorySnapshot (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.20
Nodes (10): _pick_embed_status(), _build_export(), Builds the structured JSON export dict for a pipeline report run., Assemble the machine-readable JSON export from pre-computed report data., Assemble the machine-readable JSON export from pre-computed report data., bool, float, int (+2 more)

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (6): Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool., Close the underlying HTTP client connection pool.

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (19): GraphState: review_passed field, GraphState: verification_passed field, make_graph(), Graph construction helpers for the file-edit workflow.  This module builds a `St, Decide the next graph node after the `reviewer` (static_validator) node.      -, Decide the next graph node after the `semantic_validator` node.      - If semant, Terminate early when the planner found no file to modify., Decide the next graph node after the `semantic_validator` node.      - If semant (+11 more)

### Community 36 - "Community 36"
Cohesion: 0.40
Nodes (4): Notify that similarity analysis has started., Notify that similarity analysis has started., Notify that similarity analysis has started., Notify that similarity analysis has started.

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (9): Sandbox Subprocess Execution Pattern, int, str, int, str, Helper API to run untrusted/generated Python code in a subprocess sandbox.  This, Run `code` in a subprocess with limits.      Args:         code: Python source t, run_code_in_sandbox() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.13
Nodes (18): _parse_file_list(), _parse_planner_response(), planner_node(), Planner node — selects which file(s) to modify from retrieval candidates.  When, Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root., Convert repo-relative paths to absolute paths using repo_path as the root. (+10 more)

### Community 40 - "Community 40"
Cohesion: 0.28
Nodes (16): Neo4jConfig, ReporterConfig, _build_report(), generate_report(), Query Neo4j and write a report directory containing report.md and report.json., Query Neo4j and write a report directory containing report.md and report.json., Query Neo4j and write a report directory containing report.md and report.json., Query Neo4j and write a report directory containing report.md and report.json. (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (16): DependencyEdge, FileNode, Core data types shared across the retrieval pipeline.  Defines the immutable sna, Represents a top-level symbol extracted from a file., Represents a directed import relationship between files., Metadata for a single file in the repository snapshot., Symbol, DependencyEdge (+8 more)

### Community 42 - "Community 42"
Cohesion: 0.30
Nodes (7): HeuristicRanker, Return a deterministic, ordered list of file paths., Deterministic, heuristic-based file ranker.      Ordering rules (score-based, de, bool, int, RepositorySnapshot, str

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (15): build_repository_context_payload(), _dedupe_preserve_order(), DependencySummaryItem, _normalize_path(), Versioned contract for retrieval -> coder repository context payloads.  This mod, Validate structural invariants for a repository context payload., Build a versioned, deterministic context payload from ContextPackage., RepositoryContextPayload (+7 more)

### Community 44 - "Community 44"
Cohesion: 0.11
Nodes (23): bool, diff_generator_node(), Compute a unified diff between the original and generated code.      Expected st, Validate generated code for structural correctness.      Runs Python syntax vali, static_validator_node(), Shared helpers for graph node implementations., Return a required value from `state` or raise ValueError., Remove a single pair of surrounding Markdown code fences. (+15 more)

### Community 45 - "Community 45"
Cohesion: 0.26
Nodes (8): WorkflowExecutor as Single Orchestration Boundary, Cron-based pipeline trigger.  Reads a cron expression and enqueues a PipelineTas, Executor that runs a workflow graph for a given `Task`.      The executor acce, Executor that runs a workflow graph for a given `Task`.      The executor accept, WorkflowExecutor, Task types for the scheduler.  Two concrete work units and their union — the typ, Scheduler work unit wrapping a validated TaskRequest., Task

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (14): Populate ``record.description_embedding`` in-place.          Extracts the ``summ, Populate ``record.description_embedding`` in-place.          Extracts the ``summ, Embed source code for all records in-place, respecting concurrency limit., Embed source code for all records in-place, respecting concurrency limit., Embed descriptions for all records in-place, respecting concurrency limit., Embed descriptions for all records in-place, respecting concurrency limit., Embed source code for all records in-place, respecting concurrency limit., Embed source code for all records in-place, respecting concurrency limit. (+6 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (24): bytes, bool, Path, str, str, atomic_write_bytes(), _detect_crlf(), Return True if the file contains CRLF line endings. (+16 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (20): _build_report_blocks(), notify_report_result(), Unified Slack notifications for all pipeline events.  SlackNotifier is the singl, Post a Block Kit report summary and upload the .md file on success.      Reads t, Post a Block Kit report summary and upload the .md file on success.      Reads t, Post a Block Kit report summary and upload the .md file on success.      Reads t, Post a Block Kit report summary and upload the .md file on success.      Reads t, Build a Slack Block Kit block list from a parsed report.json dict. (+12 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (9): GraphState: original_code field, _build_context_slice(), file_reader_node(), Read the target file (or select one) and return its contents.      Expected stat, Read the target file and, when a target symbol is set, build a context slice., Assemble the context dict for the coder's focused prompt., GraphState, RunContext (+1 more)

### Community 50 - "Community 50"
Cohesion: 0.09
Nodes (29): _fmt_duration(), _fmt_eta(), Post text as a thread reply, or directly to the channel if no thread is active., Post text as a thread reply, or directly to the channel if no thread is active., Format a duration in seconds as a human-readable string., Post extraction stage completion summary., Post extraction stage completion summary., Post extraction stage completion summary. (+21 more)

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (10): BudgetAllocation, Context window budget allocation.  ContextBudget enforces per-file character lim, Result of a budget allocation pass., Result of a budget allocation pass.      Attributes:         selected_files: Ord, Return the largest prefix of `ranked_files` that fits the budget.          Tar, Return the largest prefix of `ranked_files` that fits within all limits., ModelConfig, Inference settings for a single named model role.      Attributes:         name: (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.08
Nodes (43): _extract_from_file(), _is_anonymous_callback_name(), _is_test_file(), Function extractor.  Uses tree-sitter directly to walk the AST of each source fi, Return one FunctionRecord per function/method found in the repository., Return one FunctionRecord per function/method found in the repository., Return one FunctionRecord per function/method found in the repository., Return True if the relative path matches any configured test pattern. (+35 more)

### Community 54 - "Community 54"
Cohesion: 0.25
Nodes (7): FIFO Task Queue - In-memory Deterministic Ordering, TaskQueue, TaskQueue, Task, TaskDispatcher, TaskQueue, WorkflowExecutor

### Community 55 - "Community 55"
Cohesion: 0.15
Nodes (11): notify_scheduled_run(), Post a notice to Slack that a cron-triggered pipeline run has been queued., Post text as a thread reply, or directly to the channel if no thread is active., Post a notice to Slack that a cron-triggered pipeline run has been queued., CronTrigger, Fires a PipelineTask on a cron schedule.      Args:         cron_expr: Standard, Fires a PipelineTask on a cron schedule.      Args:         cron_expr: Standard, Start the background scheduling loop. Idempotent. (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.20
Nodes (11): GraphStateFactory, Build the initial GraphState from a validated TaskRequest., Converts an external TaskRequest into the internal GraphState.      This is the, External request contract for submitting a task to the LangGraph workflow., TaskRequest, Legacy task type for the LangGraph workflow system.  WorkflowTask wraps a TaskRe, Scheduler work unit wrapping a validated TaskRequest., WorkflowTask (+3 more)

### Community 57 - "Community 57"
Cohesion: 0.18
Nodes (10): ReportTask, _format_query_result(), Build a Slack mrkdwn text payload for a list of QueryMatch results., Build a Slack mrkdwn text payload for a list of QueryMatch results., Build a Slack mrkdwn text payload for a list of QueryMatch results., Routes Task instances to the appropriate handler.      Resources (OllamaClient,, Routes Task instances to the appropriate handler.      Resources (OllamaClient,, Routes Task instances to the appropriate handler.      Resources (OllamaClient, (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.11
Nodes (23): GraphState, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a sing, Shared state passed between LangGraph nodes.      This state represents a single, build_ast_graph(), graphify_indexer_node(), Run AST-only graphify extraction and write graph.json to graph_dir., Build or refresh the graphify knowledge graph for the target repository. (+15 more)

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (10): Return ``[(id, code_embedding, description_embedding)]`` for all live functions., Return ``[(id, code_embedding, description_embedding)]`` for all live functions., Return top-N code-similar functions using the HNSW vector index.          Result, Return top-N code-similar functions using the HNSW vector index.          Result, Return top-N code-similar functions using the HNSW vector index.          Result, Return top-N description-similar functions using the HNSW vector index., Return top-N description-similar functions using the HNSW vector index., Return top-N description-similar functions using the HNSW vector index. (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (11): Context Contract Version (CONTEXT_VERSION=1), Context Contract Determinism Rules, Context Contract Payload Shape, Context Contract Prompt Rendering ([REPOSITORY CONTEXT] block), Bounded Autonomy Design Principle, Mutation Exclusivity - One Active Workflow at a Time, Phase 2 - Repository Awareness, Phase 3 - Async Execution Coordinator (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.21
Nodes (9): FunctionRecord, One extracted function or method from a source file., OllamaClient, PipelineConfig, OllamaClient, PipelineConfig, int, Path (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.23
Nodes (8): Repository indexer protocol.  Defines the RepositoryIndexer interface that all i, Interface for repository indexing., Build and return an immutable repository snapshot for `root_path`., Return symbol names for a given file from the snapshot., Return dependency target paths for a given file from the snapshot., RepositoryIndexer, RepositorySnapshot, str

### Community 63 - "Community 63"
Cohesion: 0.25
Nodes (10): AppConfig, get_coder_model(), get_coder_model_config(), get_ollama_base_url(), get_primary_model(), Centralized configuration loader for the project.  Configuration is loaded from, Return the full ModelConfig for the coder role., Return the full ModelConfig for the coder role. (+2 more)

### Community 64 - "Community 64"
Cohesion: 0.20
Nodes (10): get_repository_config(), get_semantic_threshold(), Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no repo, Return the configured repository that best matches `repo_path`.      If no repo, Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass., Return the minimum task_alignment_score required for semantic_validator to pass. (+2 more)

### Community 66 - "Community 66"
Cohesion: 0.13
Nodes (15): ensure_runtime_dirs(), Centralized runtime artifact paths for deterministic CI and local runs.  All run, Create all required runtime directories if they don't exist.      Uses `parents=, Create a fresh RunContext with a new UUID4 run_id., Create a fresh RunContext with a new UUID4 run_id and current timestamp., format_run_console(), log_event(), Minimal JSONL logger and run summary writer for per-run observability events.  P (+7 more)

### Community 67 - "Community 67"
Cohesion: 0.25
Nodes (8): get_semantic_model(), get_semantic_model_config(), Return the full ModelConfig for the semantic validator role.      Prefers models, Return the full ModelConfig for the semantic validator role.      Prefers models, Return the full ModelConfig for the semantic validator role.      Prefers models, Return the model name for the semantic validator.      Prefers models["semantic_, Return the model name for the semantic validator.      Prefers models["semantic_, Return the model name for the semantic validator.      Prefers models["semantic_

### Community 68 - "Community 68"
Cohesion: 0.29
Nodes (7): get_planner_config(), PlannerConfig, Return planner settings for the repository matching ``repo_path``., Return planner settings for the repository matching ``repo_path``., Return planner settings for the repository matching ``repo_path``., Controls how many files the planner node may select for modification.      Attri, Controls how many files the planner node may select for modification.      Attri

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (12): _combined_sim(), _compute_cohesion_scores(), _compute_flags(), _cosine(), Pure Python analysis functions for the pipeline report.  These helpers operate o, Combined similarity matching the weighting used by similarity.py., Compute average pairwise similarity for each group (file or class).      Args:, Derive heuristic flag lists from pre-computed analysis data.      Returns (high_ (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.18
Nodes (12): _build_pipeline_blocks(), notify_pipeline_result(), Build a Slack Block Kit block list from a PipelineResult., Post a pipeline completion or failure notice to the configured Slack channel., Post a pipeline completion or failure notice to the configured Slack channel., Build a Slack Block Kit block list from a PipelineResult., Post a pipeline completion or failure notice to the configured Slack channel., Post a pipeline completion or failure notice to the configured Slack channel. (+4 more)

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (10): Markdown renderers for the report header and run-level overview sections.  Cover, Section 2 — delta since previous run.      Returns the markdown lines and the de, Section 2 — delta since previous run.      Returns the markdown lines and the de, Section 1 — report header and metadata table., Section 1b — one-paragraph executive summary placed after the metadata table., render_delta(), render_metadata(), render_summary() (+2 more)

### Community 72 - "Community 72"
Cohesion: 0.40
Nodes (5): Active Mode - User-triggered Code Modification, Passive Mode - Continuous Repository Analysis, Phase 1 - File Mutation MVP, Phase 4 - Passive Analysis System, TaskType (passive|active)

### Community 73 - "Community 73"
Cohesion: 0.29
Nodes (7): get_retrieval_config(), Return retrieval limits and behavior for the repository matching ``repo_path``., Return retrieval limits and behavior for the repository matching ``repo_path``., Return retrieval limits and behavior for the repository matching ``repo_path``., Controls how many files and tokens the retrieval pipeline may assemble.      Att, Controls how many files and tokens the retrieval pipeline may assemble.      Att, RetrievalConfig

### Community 74 - "Community 74"
Cohesion: 0.33
Nodes (6): _load_system_config(), Global system-level settings shared across all repositories.      Attributes:, Global system-level settings shared across all repositories.      Attributes:, Parse the top-level ``system`` block from config.json.      Falls back to ``"~/., Parse the top-level ``system`` block from config.json.      Falls back to ``"~/., SystemConfig

### Community 77 - "Community 77"
Cohesion: 0.40
Nodes (5): get_max_workflow_revision_cycles(), Return the maximum number of workflow revision cycles allowed., Return the maximum number of workflow revision cycles allowed., Return the maximum number of workflow revision cycles allowed., int

### Community 78 - "Community 78"
Cohesion: 0.50
Nodes (4): Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., Persist ``created_at`` and/or ``updated_at`` for a repository in config.json., update_repository_timestamps()

### Community 79 - "Community 79"
Cohesion: 0.09
Nodes (21): Unified Slack notifier for all pipeline events, reports, and schedule notices., Unified Slack notifier for all pipeline events, reports, and schedule notices., Unified Slack notifier for all pipeline events, reports, and schedule notices., Return a configured client, or None if Slack env vars are absent., Return a configured client, or None if Slack env vars are absent., Return a configured client, or None if Slack env vars are absent., Post the initial channel message and store thread_ts for all subsequent replies., Post the initial channel message and store thread_ts for all subsequent replies. (+13 more)

### Community 80 - "Community 80"
Cohesion: 0.21
Nodes (13): Markdown renderers for code-quality analysis sections.  Covers: File Cohesion, C, Section 13 — heuristic flags raised by the analysis., Section 10 — file cohesion scores (ascending, most fragmented first)., Section 11 — class cohesion scores (omitted when no classes present)., Section 12 — duplication clusters at the configured similarity threshold., render_class_cohesion(), render_duplication_clusters(), render_file_cohesion() (+5 more)

### Community 81 - "Community 81"
Cohesion: 0.12
Nodes (15): EmbeddingService, Embedding service for code and description vectors.  Wraps ``OllamaClient.embed(, Generates code and description embeddings using OllamaClient., Generates code and description embeddings using OllamaClient., Generates code and description embeddings using OllamaClient., Populate ``record.code_embedding`` and ``record.code_embedding_status`` in-place, Populate ``record.code_embedding`` and ``record.code_embedding_status`` in-place, Split text into overlapping windows of _CHUNK_SIZE_CHARS with _CHUNK_OVERLAP_CHA (+7 more)

### Community 82 - "Community 82"
Cohesion: 0.09
Nodes (23): PipelineResult, Summary of a completed pipeline run., Slack notification settings for pipeline observability., Slack notification settings for pipeline observability., Slack notification settings for pipeline observability., Summary of a completed pipeline run., Summary of a completed pipeline run., Summary of a completed pipeline run. (+15 more)

### Community 83 - "Community 83"
Cohesion: 0.20
Nodes (8): _ddl(), Idempotently create constraints and indexes.          Args:             vector_d, Execute a read Cypher query and return all result rows as dicts., Idempotently create constraints and indexes.          Args:             vector_d, Format a DDL template with integer-only substitutions and assert LiteralString., LiteralString, int, Neo4jConfig

### Community 84 - "Community 84"
Cohesion: 0.36
Nodes (7): FunctionExtractor, Extracts every function and method from a repository as FunctionRecords.      Em, Extracts every function and method from a repository as FunctionRecords.      Em, Extracts every function and method from a repository as FunctionRecords.      Em, SlackNotifier, bool, PipelineConfig

### Community 85 - "Community 85"
Cohesion: 0.28
Nodes (7): Execute all pipeline stages and return a summary., Execute all pipeline stages and return a summary., Execute all pipeline stages and return a summary., Execute all pipeline stages and return a summary., Execute all pipeline stages and return a summary., PipelineResult, PipelineResult

### Community 86 - "Community 86"
Cohesion: 0.33
Nodes (5): Post a sync summary and, when debug_messages is on, operation detail., Post a sync summary and, when debug_messages is on, operation detail., Post a sync summary and, when debug_messages is on, operation detail., Post a sync summary and, when debug_messages is on, operation detail., SyncResult

### Community 87 - "Community 87"
Cohesion: 0.20
Nodes (8): _compute_clusters(), _find_previous_report(), Build connected components from similarity edges via BFS.      Each node is iden, Return the most informative non-ok embed status for a function row.      Prefers, Return the parsed JSON of the most recent prior report, or None., Return the parsed JSON of the most recent prior report, or None., Post-run report generator.  Queries Neo4j after a pipeline run and writes a stru, Path

### Community 88 - "Community 88"
Cohesion: 0.29
Nodes (5): The configured Neo4j database name., Return qualifiedName, filePath, and description for each requested function id., Return qualifiedName, filePath, and description for each requested function id., Return qualifiedName, filePath, and description for each requested function id., str

### Community 89 - "Community 89"
Cohesion: 0.29
Nodes (6): Markdown renderers for the embedding and description integrity section., Section 3 — embedding and description coverage tables., Section 3 — embedding and description coverage tables., render_embedding_integrity(), int, str

### Community 90 - "Community 90"
Cohesion: 0.40
Nodes (4): Notify that an embedding stage has started., Notify that an embedding stage has started., Notify that an embedding stage has started., Notify that an embedding stage has started.

### Community 91 - "Community 91"
Cohesion: 0.50
Nodes (3): Close the driver connection pool., Close the driver connection pool., Close the driver connection pool.

### Community 92 - "Community 92"
Cohesion: 0.15
Nodes (12): GraphState: generated_code field, file_writer_node(), Write generated content to disk or apply a unified diff.      Expected state inp, Write generated content to disk or apply a unified diff.      Expected state inp, git_committer_node(), Stage and commit the modified target file.      Expected state keys:     - ``, Stage and commit the modified target file.      Expected state keys:     - ``rep, Aggregate export surface for graph nodes. (+4 more)

### Community 93 - "Community 93"
Cohesion: 0.40
Nodes (4): Notify that repository synchronisation has started., Notify that repository synchronisation has started., Notify that repository synchronisation has started., Notify that repository synchronisation has started.

### Community 94 - "Community 94"
Cohesion: 0.50
Nodes (3): Delete all SIMILAR_TO edges originating from functions in this repo.          Ca, Delete all SIMILAR_TO edges originating from functions in this repo.          Ca, Delete all SIMILAR_TO edges originating from functions in this repo.          Ca

### Community 95 - "Community 95"
Cohesion: 0.50
Nodes (3): Return ``{function_id: source_hash}`` for all live functions in the repo., Return ``{function_id: source_hash}`` for all live functions in the repo., Return ``{function_id: source_hash}`` for all live functions in the repo.

### Community 96 - "Community 96"
Cohesion: 0.50
Nodes (3): Mark functions not in ``seen_ids`` as deleted. Returns count., Mark functions not in ``seen_ids`` as deleted. Returns count., Mark functions not in ``seen_ids`` as deleted. Returns count.

## Knowledge Gaps
- **36 isolated node(s):** `str`, `float`, `str`, `int`, `bool` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `datetime` connect `Community 48` to `Test Infrastructure & Fixtures`, `Community 40`, `Community 45`, `Community 82`, `Community 19`, `Community 87`, `Community 28`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `GraphState` connect `Community 58` to `Community 33`, `Community 66`, `Community 39`, `Community 9`, `Community 43`, `Community 44`, `Community 45`, `Community 92`, `Community 49`, `Community 56`, `Community 26`, `Community 28`, `Community 29`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `OllamaClient` connect `Community 2` to `Community 32`, `LLM Pipeline & Sandbox`, `Community 12`, `Community 44`, `Community 46`, `Community 81`, `Community 19`, `Community 84`, `Community 85`, `Community 57`, `Community 61`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `GraphState` (e.g. with `RepositoryContextPayload` and `RetrievalResult`) actually correct?**
  _`GraphState` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 47 inferred relationships involving `RunContext` (e.g. with `GraphConfig` and `GraphHandle`) actually correct?**
  _`RunContext` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `PipelineConfig` (e.g. with `DescriptionService` and `EmbeddingService`) actually correct?**
  _`PipelineConfig` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `Neo4jStore` (e.g. with `FunctionRecord` and `Neo4jConfig`) actually correct?**
  _`Neo4jStore` has 36 INFERRED edges - model-reasoned connections that need verification._