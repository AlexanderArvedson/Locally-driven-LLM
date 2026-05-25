# PROJECT PLAN

## Project Overview

This project explores locally hosted, tool-augmented LLM systems for continuous software maintenance and bounded repository evolution.

The system is designed around asynchronous autonomous workflows rather than interactive chat-based coding assistance.

Primary goals:
- Repository health monitoring
- Maintainability analysis
- Automated refactoring support
- Documentation drift detection
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

Passive mode does not directly modify code.

---

## Active Mode

An active execution workflow is triggered when a user selects a reported issue.

Responsibilities:
- retrieve repository context
- plan modifications
- generate changes
- verify changes through tooling
- iterate until stable output is achieved
- produce final patches or proposed changes

This mode is intentionally asynchronous and long-running.

---

# Initial Focus Areas

## 1. Refactoring & Maintainability

Primary target area.

Examples:
- oversized functions/classes
- naming inconsistencies
- responsibility violations
- duplicated logic
- structural simplification

---

## 2. Repository Hygiene

Examples:
- dead code
- stale abstractions
- unused imports/functions
- orphaned modules

---

## 3. Documentation Drift Detection

Examples:
- outdated README content
- mismatched API documentation
- missing docstrings
- implementation vs documentation inconsistencies

---

## 4. Bounded Code Generation

Later-stage capability.

Focus:
- constrained subsystem modifications
- architecture-consistent extensions
- retrieval-assisted generation

---

# Architectural Direction

## Planned Workflow

1. Repository scan
2. Static analysis
3. LLM-assisted reasoning
4. Issue ranking
5. User issue selection
6. Context retrieval
7. Code modification
8. Verification loop
9. Retry/refinement
10. Final output

---

# Retrieval Strategy

The system will likely combine:
- AST analysis
- dependency graphs
- symbol extraction
- keyword search
- embeddings/vector retrieval
- repository metadata

Embeddings are treated as one component of a larger retrieval pipeline rather than the primary source of understanding.

---

# Current Architecture (MVP)

## Existing Components

- Ollama integration
- Async LLM client
- LangGraph workflow
- Basic graph state
- Initial coder node

---

# Immediate Next Steps

## Phase 1 — Functional MVP

- [ ] file read/write tooling
- [ ] repository-aware prompts
- [ ] structured graph state
- [ ] review node
- [ ] verification node
- [ ] retry loop
- [ ] basic issue execution flow

---

## Phase 2 — Repository Awareness

- [ ] AST parsing
- [ ] symbol extraction
- [ ] repository indexing
- [ ] context builder service
- [ ] retrieval pipeline

---

## Phase 3 — Passive Analysis System

- [ ] scheduled scans
- [ ] issue persistence
- [ ] ranking/scoring
- [ ] reporting layer

---

## Phase 4 — Advanced Maintenance Workflows

- [ ] multi-agent orchestration
- [ ] evaluator agents
- [ ] automated refinement loops
- [ ] constrained subsystem evolution

---

# Research Questions

The project aims to evaluate:
- effectiveness of local LLMs for maintenance workflows
- orchestration vs model capability tradeoffs
- retrieval quality vs output quality
- iterative verification reliability
- bounded autonomy in software engineering systems

---

# Current Status

Current stage:
Early infrastructure and workflow prototyping.

Working components:
- Ollama-based local inference
- LangGraph execution flow
- basic generation node
- graph state handling

Current priority:
repository-aware execution and file modification workflows