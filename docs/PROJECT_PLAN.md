Last updated: 2026-05-26

# PROJECT PLAN

## Project Overview

This project explores locally hosted, tool-augmented LLM systems for continuous software maintenance and bounded repository evolution.

The system is designed around asynchronous workflow orchestration for future autonomous maintenance operations rather than interactive chat-based coding assistance.

Primary goals:
- Repository health monitoring
- Maintainability analysis
- Automated refactoring support (beyond MVP)
- Documentation drift detection (beyond MVP)
- Constrained code modification
- Verification-driven iteration loops

The project prioritizes:
- reliability over latency
- bounded autonomy over unrestricted generation
- orchestration quality over raw model capability

---

# Core Concept

The system operates in two modes:

## Passive Mode

A scheduled agent continuously analyzes repositories.

Responsibilities:
- detect maintainability issues
- identify architectural degradation
- surface dead code
- detect documentation drift
- monitor codebase hygiene
- generate ranked findings

Passive mode does not modify code.

---

## Active Mode

Triggered when a user selects a reported issue.

Responsibilities:
- retrieve repository context
- plan modifications
- generate changes
- verify changes through tooling
- iterate until stable output is achieved
- produce final patches or proposed changes

---

# Initial Focus Areas

## 1. Refactoring & Maintainability
- oversized functions/classes
- naming inconsistencies
- responsibility violations
- duplicated logic
- structural simplification

## 2. Repository Hygiene
- dead code
- stale abstractions
- unused imports/functions
- orphaned modules

## 3. Documentation Drift Detection
- outdated README content
- mismatched API documentation
- missing docstrings
- implementation vs documentation inconsistencies

## 4. Bounded Code Generation (later stage)
- constrained subsystem modifications
- architecture-consistent extensions
- retrieval-assisted generation

---

# Architecture Direction

## Planned Workflow

1. Repository scan (MVP simulated)
2. Static analysis (basic / implicit)
3. LLM-assisted reasoning
4. Issue ranking system (not yet implemented)
5. User selection (test-driven input)
6. Context retrieval (single-file MVP)
7. Code modification
8. Verification loop
9. Retry/refinement
10. Final output

---

# Retrieval Strategy

The system will combine:

- AST analysis
- dependency graphs
- symbol extraction
- keyword search
- embeddings/vector retrieval
- repository metadata

Embeddings are one component, not the core mechanism.

---

# Current Architecture (MVP)

## Implemented Components

- Ollama integration
- Async LLM client
- LangGraph workflow
- Graph state model
- Initial coder node
- File mutation pipeline (single-file MVP)
- Repository indexing (AST-only `SimpleRepositoryIndexer`)
- Deterministic retrieval engine (`SimpleRetrievalEngine`)
- Bounded Context Builder (`SimpleContextBuilder`)
- Versioned retrieval/coder contract (`src/repository/context_contract.py`)
- `context_builder_node` integrated into graph between `file_reader` and `coder`
- Deterministic prompt formatting enforced at the coder boundary
- Unit and integration tests for indexer, retrieval, context builder, and contract
- Test fixtures and a shared `httpx` stub helper for import-time stability

---

## File Mutation MVP (Phase 1 — COMPLETED BASELINE)

The system currently supports:

- [x] deterministic file read/write
- [x] full-file context injection into LLM
- [x] unified diff generation
- [x] diff application with safety checks
- [x] reviewer node (syntax / basic lint gating)
- [x] verifier node (execution smoke test)
- [x] retry loop (bounded iterations)
- [x] safe writer (abort-on-failure)
- [x] failed artifact persistence (`.runtime/failed_patches/`)
- [x] smoke + unit test coverage for patching

---

## Key Files

- `src/tools/files.py` — file I/O
- `src/tools/patches.py` — diff generation + application
- `src/graph/nodes/nodes.py` — coder, reviewer, verifier, writer
- `src/graph/workflow.py` — execution graph
- `scripts/test_file_edit.py` — smoke test
- `tests/test_patches.py` — unit tests

---

# Phase 1 — File Mutation MVP (Active Definition)

## Goal

Modify a real file via LLM-generated diff with full safety gating.

## Execution Guarantees

A run is valid only if:

- [x] no uncontrolled file overwrite occurs
- [x] diff is either applied or rejected deterministically
- [x] verifier executes and produces pass/fail
- [x] failed outputs are persisted in `.runtime/failed_patches/`

---

## Observability

### 1. Structured Logging (system truth layer)

Each node must emit JSON logs with:

- [ ] node_name
- [ ] task_id
- [ ] model_used
- [ ] input/output summary
- [ ] duration_ms
- [ ] success/failure
- [ ] retry iteration
- [ ] file operations

Purpose:
- debugging
- reproducibility
- evaluation dataset creation

---

### 2. Langfuse (LLM observability layer)

Optional tracing system for:

- [ ] prompt/completion tracking
- [ ] token usage
- [ ] workflow spans
- [ ] model comparison
- [ ] execution trace history

Purpose:
- experiment tracking
- prompt iteration
- model benchmarking

---

## Phase 1 Completion Criteria

Phase 1 is complete when:

- [x] CI runs tests + runtime log validation
- [x] structured logs exist for all nodes
- [x] failed patches are persisted reliably
- [x] diff application is deterministic
- [x] verifier gate is enforced before write
- [ ] optional Langfuse integration is implemented

---

### Observability implementation status

- Implemented: per-run JSONL logs written to `.runtime/runs/<run_id>.jsonl` with one event per node execution. Each event contains the fixed top-level shape: `run_id`, `node`, `status`, `duration_ms`, `task`, `payload`.
- Implemented fields: `node` (node name), `task` (task string), `model` (in `payload` for LLM-using nodes), `duration_ms`, `status` (success/failure), and compact `payload` entries such as `original_length`, `diff_length`, `updated_length`, and `error` on failures.
- Notes / next steps:
	- `retry_iteration` is not added as a top-level field; retries are represented by repeated node-execution events. If a top-level iteration is required for easier aggregation, consider adding it to the node `payload` rather than modifying `GraphState` for this phase.
	- CI enforcement (run + artifact validation) is still outstanding and should be added to ensure traces are always produced in automated runs.
	- Langfuse remains out of scope for Phase 1 and will be added later as a mirror/adapter.

---

## Phase 2 — Repository Awareness

Reference documentation:
- `docs/CONTEXT_CONTRACT.md` (authoritative retrieval -> coder context contract)

## Goal

Extend beyond single-file mutation into deterministic, bounded repository-aware reasoning used to assemble prompts.

## Tasks and Status

- [x] AST parsing (indexer extracts symbols via stdlib `ast`)
- [x] symbol extraction (deterministic symbol lists per file)
- [x] repository indexing (`SimpleRepositoryIndexer` — snapshot per run)
- [x] context builder service (`SimpleContextBuilder` — bounded `ContextPackage`)
- [x] retrieval pipeline (`SimpleRetrievalEngine` — deterministic heuristics)
- [x] cross-file dependency awareness (dependency summary in context payload)
- [x] retrieval/coder contract (versioned serializer + validator)
- [x] graph node wiring (`context_builder_node`) and prompt boundary enforcement
- [x] Optional: extend retrieval heuristics and ranking 

---

# Phase 3 — Execution & Scheduling Layer

## Goal

Introduce a deterministic execution layer responsible for orchestrating repository analysis runs independently of analysis logic or LLM workflows.

This phase establishes the control plane for Passive Mode and future autonomous workflows.

The scheduler is responsible for:

- deciding when runs occur
- selecting repositories/tasks
- managing execution lifecycle
- enforcing concurrency boundaries
- persisting execution metadata
- coordinating workflow invocation

The scheduler does not perform repository analysis itself.

## Responsibilities

### 1. Scheduled Execution

Support deterministic scheduled repository scans.

Initial scope:

- interval-based execution
- manually triggerable runs
- single-process scheduling

Future scope:

- cron expressions
- distributed execution
- event-driven triggers

### 2. Run Lifecycle Management

Introduce a formal run lifecycle.

Example states:

- pending
- queued
- running
- completed
- failed
- cancelled

Responsibilities:

- create run records
- track execution status
- persist timestamps
- record failures
- support retries/backoff

### 3. Repository Task Selection

Define how repositories are selected for execution.

Initial MVP:

- static configured repository list
- sequential processing

Future work:

- prioritization
- adaptive scheduling
- issue-driven execution
- cooldown windows

### 4. Workflow Invocation Boundary

The scheduler invokes workflows but remains separate from LangGraph internals.

Responsibilities:

- construct execution request
- provide runtime metadata
- launch workflow
- collect execution result

The scheduler must not:

- contain LLM logic
- contain retrieval logic
- contain patch-generation logic

### 5. Concurrency Control

Introduce bounded execution guarantees.

Initial constraints:

- one active workflow per repository
- optional global concurrency limit
- deterministic execution order

Future work:

- distributed workers
- priority queues
- resource-aware scheduling

### 6. Persistence Layer

Persist execution metadata independently from node-level JSONL traces.

Possible persisted data:

- run ID
- repository
- workflow type
- execution timestamps
- completion state
- failure reason
- retry count

Initial implementation may use:

- SQLite
- JSON state files

### 7. Failure Handling & Recovery

Introduce scheduler-level recovery behavior.

Responsibilities:

- retry failed runs
- bounded retry policy
- failure persistence
- orphaned run cleanup
- timeout handling

This is distinct from:

- reviewer retries
- verifier retries
- LLM refinement loops

### 8. Execution Identity Model

Each scheduled execution should receive:

- globally unique run ID
- immutable execution metadata
- trace linkage across scheduler/runtime logs

This identity model is useful for:

- Langfuse integration
- evaluation harnesses
- replay and debugging
- benchmark reproducibility

## Initial Architecture Direction

### Proposed Components

- SchedulerService
	- execution loop
	- interval management
	- task dispatch
- RunRegistry
	- execution persistence
	- run status tracking
- RepositoryQueue
	- repository scheduling order
	- concurrency enforcement
- WorkflowExecutor
	- isolated LangGraph invocation boundary

### Initial Execution Flow

- Scheduler tick occurs
- Repository selected
- Run record created
- Workflow execution launched
- Runtime logs emitted
- Run state updated
- Results persisted

## Phase 3 Completion Criteria

Phase 3 is complete when:

- repositories can be scheduled deterministically
- workflows execute through scheduler orchestration
- run lifecycle states are persisted
- scheduler failures are recoverable
- repository concurrency constraints are enforced
- manual and scheduled execution both function
- scheduler logic is isolated from LangGraph workflow logic

## Non-Goals (Current Phase)

The following are explicitly out of scope:

- distributed scheduling
- Kubernetes orchestration
- multi-machine execution
- cloud-native scaling
- event-stream infrastructure
- advanced queue brokers
- autonomous issue prioritization
- self-modifying scheduling policies

## Notes

The scheduling layer is considered infrastructure orchestration, not analysis logic.

This separation exists to preserve:

- deterministic execution
- bounded autonomy
- reproducibility
- testability
- workflow isolation

---

# Phase 4 — Passive Analysis System

- [ ] repository analysis execution
- [ ] maintainability analysis
- [ ] issue detection
- [ ] ranking/scoring
- [ ] persistence layer
- [ ] report generation

---

# Phase 5 — Advanced Maintenance Workflows

- [ ] multi-agent orchestration
- [ ] evaluator loops
- [ ] automated refinement cycles
- [ ] constrained subsystem evolution

---

## Current Status

## Stage

Phase 1 — File Mutation MVP: Completed. Phase 2 — Repository Awareness: initial implementation completed and integrated. Phase 3 — Execution & Scheduling Layer: design and implementation pending.

## Working capabilities

- [x] Local LLM via Ollama (local/integration only)
- [x] LangGraph orchestration
- [x] Safe file modification loop with verifier and reviewer gates
- [x] Deterministic per-run JSONL observability (`.runtime/runs/*.jsonl`)
- [x] Persisted failed artifacts (`.runtime/failed_patches/`)
- [x] Unit tests + integration tests covering indexer, retrieval, context builder, node wiring, and prompt contract
- [x] Deterministic repository snapshotting and normalized, versioned context payloads
- [x] Test fixtures and helpers to stabilize import-time dependencies

## Current focus

Stabilize and consolidate Phase 2 repository-awareness infrastructure; short-term priorities:

- Begin Phase 3 execution/scheduling layer design
- Define scheduler/runtime boundaries before passive analysis implementation

---

# Research Questions

- effectiveness of local LLMs in maintenance automation
- orchestration vs model capability tradeoffs
- retrieval quality impact on correctness
- reliability of iterative verification loops
- bounded autonomy in software engineering systems