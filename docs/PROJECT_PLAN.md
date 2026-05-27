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

### Passive Workflow

1. Scheduler trigger
2. Repository selection
3. Deterministic repository snapshot generation
4. Static analysis (basic / implicit)
5. LLM-assisted reasoning
6. Issue ranking/scoring
7. Finding persistence/report generation

### Active Workflow

1. User selects issue
2. Context retrieval
3. Modification planning
4. Code generation
5. Verification/reviewer loop
6. Retry/refinement
7. Final patch generation

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

# Phase 3 — Async Execution Coordinator (MVP)

## Goal

Introduce a minimal asyncio-based execution layer that orchestrates workflow execution.

It is responsible only for:
- launching workflows
- ensuring only one mutation workflow runs at a time
- queueing additional tasks
- providing a single controlled entrypoint for passive and active execution

No persistence system, no scheduler platform, no recovery layer.

---

## Core Responsibilities

### 1. Async Execution Loop

- Run a single long-lived asyncio loop
- Accept execution requests (passive or active)
- Dispatch workflows through a unified executor
- Maintain deterministic FIFO ordering for queued tasks

---

### 2. Mutation Exclusivity

- Only one active mutation workflow may execute at any time
- Subsequent mutation requests must queue
- System must block or defer execution until active workflow completes

---

### 3. Task Queueing

- Maintain an in-memory queue of workflow requests
- FIFO ordering (no prioritization in this phase)
- Tasks are either:
  - passive analysis
  - active mutation

---

### 4. Workflow Invocation Boundary

- All workflows are executed via a single `WorkflowExecutor`
- The execution layer must NOT contain:
  - LLM logic
  - retrieval logic
  - patch generation logic
  - repository indexing logic

Its only responsibility is orchestration.

---

## Explicit Non-Goals

Do NOT implement:

- persistence layer (SQLite, run registry, lifecycle DB)
- formal state machines (pending/running/failed/etc.)
- retry/backoff systems
- crash recovery or orphan detection
- distributed execution or multi-process scheduling
- cron systems or external schedulers
- priority queues or adaptive scheduling
- workflow introspection or dependency tracking

---

## Minimal Architecture

- `ExecutionLoop`
  - owns asyncio lifecycle
  - consumes task queue
  - enforces mutation exclusivity

- `TaskQueue`
  - in-memory FIFO queue of workflow requests

- `WorkflowExecutor`
  - single entrypoint for running LangGraph workflows

---

## Execution Model

1. Task is submitted (passive or active)
2. Task is enqueued
3. ExecutionLoop polls queue
4. If task is:
   - passive → run if no mutation active OR run inline (implementation choice)
   - active → requires exclusive execution slot
5. WorkflowExecutor runs workflow
6. Loop continues

No lifecycle tracking beyond “running now / not running”.

---

## Key Design Constraints

- Single-process only
- In-memory state only
- No persistence requirements
- Deterministic execution order (FIFO)
- One active mutation workflow globally
- Strict separation between orchestration and workflow logic

---

## Phase 3 Checklist

### Core Implementation

- [ ] Implement asyncio `ExecutionLoop`
- [ ] Implement in-memory `TaskQueue`
- [ ] Implement `Task` model (passive / active)
- [ ] Implement mutation exclusivity guard
- [ ] Integrate with existing `WorkflowExecutor`

---

### Execution Semantics

- [ ] Ensure only one mutation workflow runs at a time
- [ ] Ensure queued mutation tasks execute in order
- [ ] Ensure passive tasks do not interfere with mutation execution
- [ ] Ensure deterministic FIFO behavior

---

### Integration

- [ ] Provide simple API: `submit_task(task)`
- [ ] Wire execution loop into existing graph executor
- [ ] Verify no scheduler logic leaks into LangGraph nodes

---

## Definition of Done

Phase 3 is complete when:

- workflows can be submitted asynchronously
- mutation workflows never overlap
- queued tasks execute sequentially
- system runs continuously in a single process
- orchestration layer remains isolated from analysis logic

# Phase 4 — Passive Analysis System

- [ ] repository analysis execution
- [ ] maintainability analysis
- [ ] issue detection
- [ ] finding classification/normalization
- [ ] ranking/scoring
- [ ] persistence layer
- [ ] report generation
- [ ] finding lifecycle (deduplication, aging, suppression, state transitions) (future implementation most likely)

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