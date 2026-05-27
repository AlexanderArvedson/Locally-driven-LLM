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

# Phase 3 — Execution & Scheduling Layer

## Goal

Introduce a deterministic execution layer responsible for orchestrating repository analysis and workflow execution independently from analysis logic or LangGraph internals.

This phase establishes the control plane for Passive Mode and future autonomous workflows.

The scheduler is responsible for:

- deciding when executions occur
- scheduling passive and active workflows
- managing execution lifecycle
- enforcing concurrency boundaries
- persisting execution metadata
- coordinating workflow invocation

The scheduler does not perform repository analysis itself.

---

## Responsibilities

### 1. Scheduled Execution

Support deterministic scheduled repository state analysis runs.

Initial scope:

- interval-based execution
- manually triggerable runs
- single-process scheduling

Future scope:

- cron expressions
- event-driven triggers
- distributed execution

---

### 2. Run Lifecycle Management

Introduce a formal execution lifecycle.

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
- detect stale/orphaned executions

Scheduler recovery logic should support stale-run detection through heartbeat timestamps or execution timeout policies.

This lifecycle is infrastructure-level orchestration and remains separate from workflow-specific retry/refinement behavior.

---

### 3. Task Scheduling & Execution Coordination

Define how passive and active execution tasks are scheduled and dispatched.

Initial MVP:

- static configured execution scheduling
- sequential mutation workflow execution
- deterministic task ordering

Future work:

- prioritization
- adaptive scheduling
- issue-driven execution
- cooldown windows
- policy-aware scheduling

The scheduling layer coordinates execution timing and orchestration but does not determine repository invalidation scope or dependency relationships.

Incremental analysis scope determination is delegated to repository indexing and invalidation components introduced in later phases.

---

### 4. Workflow Invocation Boundary

The scheduler invokes workflows but remains isolated from LangGraph internals and repository analysis logic.

Responsibilities:

- construct execution request
- provide runtime metadata
- launch workflow execution
- collect execution result
- persist execution outcome

The scheduler must not:

- contain LLM logic
- contain retrieval logic
- contain patch-generation logic
- contain repository indexing logic
- contain dependency invalidation logic

The `WorkflowExecutor` acts as the isolation boundary between orchestration infrastructure and runtime workflow execution.

---

### 5. Execution Coordination & Concurrency Control

The system intentionally limits mutation-oriented workflows to a single active execution at a time while allowing passive analysis workflows to execute concurrently under controlled conditions.

This preserves deterministic repository state and simplifies verification semantics.

Goals:

- preserve deterministic repository state
- avoid overlapping patch generation
- simplify verification semantics
- reduce synchronization complexity
- prevent workspace contamination across executions

Initial constraints:

- one active code-modification workflow globally
- mutation workflows receive exclusive repository access
- passive analysis workflows are strictly read-only
- passive analysis may execute concurrently only when repository state is stable
- active workflow requests queue while a mutation workflow is running
- deterministic execution ordering for queued tasks

Future work:

- limited parallel passive analysis
- priority-aware queueing
- repository snapshot isolation
- worktree-based execution isolation

---

### 6. Repository State Guarantees

Each execution must operate against a deterministic repository state.

Core guarantees:

- executions begin from a known git state
- incomplete mutations must not persist across runs
- workspace contamination between executions is prohibited
- failed workflows must restore or discard invalid workspace state
- verifier execution must observe deterministic filesystem state

These guarantees exist to preserve:

- reproducibility
- benchmark stability
- deterministic verification
- replayability
- evaluation consistency

---

### 7. Persistence Layer

Persist execution metadata independently from node-level JSONL traces.

Possible persisted data:

- run ID
- workflow type
- execution mode
- execution timestamps
- completion state
- failure reason
- retry count
- policy violations
- execution metadata
- analysis version

Initial implementation may use:

- SQLite
- JSON state files

Execution persistence should remain independent from workflow implementation details.

---

### 8. Failure Handling & Recovery

Introduce scheduler-level recovery behavior.

Responsibilities:

- retry failed runs
- bounded retry policy
- failure persistence
- orphaned run cleanup
- timeout handling
- stale-run recovery

This is distinct from:

- reviewer retries
- verifier retries
- LLM refinement loops
- runtime graph recovery behavior

Scheduler-level recovery is infrastructure orchestration, not workflow reasoning.

---

### 9. Execution Identity Model

Each execution should receive:

- globally unique run ID
- immutable execution metadata
- trace linkage across scheduler/runtime logs

This identity model is useful for:

- Langfuse integration
- evaluation harnesses
- replay and debugging
- benchmark reproducibility
- artifact correlation
- runtime observability

The run ID should act as the primary correlation identifier across all runtime systems and persisted artifacts.

---

## Initial Architecture Direction

### Proposed Components

- `ExecutionScheduler`
  - periodic execution loop
  - interval management
  - task dispatch coordination

- `MutationQueue`
  - queued mutation workflow requests
  - deterministic execution ordering

- `RunRegistry`
  - execution persistence
  - run status tracking
  - lifecycle management

- `WorkflowExecutor`
  - isolated workflow invocation boundary
  - policy enforcement
  - runtime execution coordination

---

## Initial Execution Flow

- Scheduler tick occurs
- Execution eligibility evaluated
- Passive analysis execution launched if scheduled
- Active task submitted manually or externally
- `MutationQueue` enqueues mutation request
- When no mutation workflow is active, next task is dispatched
- Run record created
- `WorkflowExecutor` launches workflow execution
- Runtime logs emitted
- Execution result collected
- Run state updated
- Results persisted

---

## Phase 3 Completion Criteria

Phase 3 is complete when:

- [ ] executions can be scheduled deterministically
- [ ] workflows execute through scheduler orchestration
- [ ] run lifecycle states are persisted
- [ ] scheduler failures are recoverable
- [ ] repository concurrency constraints are enforced
- [ ] manual and scheduled execution both function
- [ ] scheduler logic remains isolated from LangGraph workflow logic
- [ ] deterministic repository state guarantees are enforced

---

## Non-Goals (Current Phase)

The following are explicitly out of scope:

- distributed scheduling
- Kubernetes orchestration
- multi-machine execution
- cloud-native scaling
- event-stream infrastructure
- advanced queue brokers
- autonomous issue prioritization
- semantic dependency invalidation
- repository-wide incremental indexing
- self-modifying scheduling policies

---

## Notes

The scheduling layer is considered infrastructure orchestration, not analysis logic.

This separation exists to preserve:

- deterministic execution
- bounded autonomy
- reproducibility
- testability
- workflow isolation
- evaluation consistency

Passive Mode incremental invalidation, repository indexing, and dependency graph analysis are introduced in later phases and remain outside scheduler responsibilities.

---

## Operational Safety Model

Centralized workflow and repository safety constraints that bound mutations and runtime behavior. These are global, system-level guarantees and not specific to scheduling.

Core constraints:

- writable path restrictions (deny-list and allow-list)
- max patch size (lines/bytes)
- forbidden file classes (generated, vendor, large binaries)
- bounded modification scope (per-run file/file-change limits)
- execution timeout policy (per-workflow and per-node)
- verifier hard-failure rules (abort and persist failed artifacts)

Governance & policy notes:

- policies are enforced at the `WorkflowExecutor` boundary
- policies are independent of scheduling and apply to both passive and active workflows
- policies should be configurable per-deployment
- policy decisions should be auditable through runtime logs
- policy enforcement must remain deterministic and reproducible

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