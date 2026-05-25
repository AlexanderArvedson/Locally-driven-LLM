Last updated: 2026-05-25

# PROJECT PLAN

## Project Overview

This project explores locally hosted, tool-augmented LLM systems for continuous software maintenance and bounded repository evolution.

The system is designed around asynchronous autonomous workflows rather than interactive chat-based coding assistance.

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

- [] node_name
- [] task_id
- [] model_used
- [] input/output summary
- [] duration_ms
- [] success/failure
- [] retry iteration
- [] file operations

Purpose:
- debugging
- reproducibility
- evaluation dataset creation

---

### 2. Langfuse (LLM observability layer)

Optional tracing system for:

- [] prompt/completion tracking
- [] token usage
- [] workflow spans
- [] model comparison
- [] execution trace history

Purpose:
- experiment tracking
- prompt iteration
- model benchmarking

---

## Phase 1 Completion Criteria

Phase 1 is complete when:

- [] CI runs tests + runtime log validation
- [x] structured logs exist for all nodes
- [x] failed patches are persisted reliably
- [x] diff application is deterministic
- [x] verifier gate is enforced before write
- [] optional Langfuse integration is implemented

---

### Observability implementation status

- Implemented: per-run JSONL logs written to `.runtime/runs/<run_id>.jsonl` with one event per node execution. Each event contains the fixed top-level shape: `run_id`, `node`, `status`, `duration_ms`, `task`, `payload`.
- Implemented fields: `node` (node name), `task` (task string), `model` (in `payload` for LLM-using nodes), `duration_ms`, `status` (success/failure), and compact `payload` entries such as `original_length`, `diff_length`, `updated_length`, and `error` on failures.
- Notes / next steps:
	- `retry_iteration` is not added as a top-level field; retries are represented by repeated node-execution events. If a top-level iteration is required for easier aggregation, consider adding it to the node `payload` rather than modifying `GraphState` for this phase.
	- CI enforcement (run + artifact validation) is still outstanding and should be added to ensure traces are always produced in automated runs.
	- Langfuse remains out of scope for Phase 1 and will be added later as a mirror/adapter.

---

# Phase 2 — Repository Awareness

## Goal

Extend beyond single-file mutation into repository-wide reasoning.

## Tasks

- [] AST parsing
- [] symbol extraction
- [] repository indexing
- [] context builder service
- [] retrieval pipeline
- [] cross-file dependency awareness

---

# Phase 3 — Passive Analysis System

- [] scheduled scans
- [] issue detection
- [] ranking/scoring
- [] persistence layer
- [] report generation

---

# Phase 4 — Advanced Maintenance Workflows

- [] multi-agent orchestration
- [] evaluator loops
- [] automated refinement cycles
- [] constrained subsystem evolution

---

# Current Status

## Stage

Early infrastructure + working file mutation MVP.

## Working capabilities

- [x] local LLM via Ollama
- [x] LangGraph orchestration
- [x] safe file modification loop
- [x] verification-driven execution

## Current focus

Stabilize Phase 1 + add observability + CI enforcement.

---

# Research Questions

- effectiveness of local LLMs in maintenance automation
- orchestration vs model capability tradeoffs
- retrieval quality impact on correctness
- reliability of iterative verification loops
- bounded autonomy in software engineering systems