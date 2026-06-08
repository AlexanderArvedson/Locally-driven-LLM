# Locally-driven-langgraph-LLM

A pipeline that scans a source repository, extracts every function and method, generates vector embeddings and LLM descriptions via Ollama, stores the results in Neo4j, and builds a weighted similarity graph — useful for code search, duplicate detection, and architectural analysis. Everything runs locally; no data leaves your machine.

---

## Quick start

```bash
cp .env.example .env          # fill in NEO4J_PASSWORD and REPOS_ROOT
cp config.example.json config.json  # fill in name and local_path for your repo
docker compose up -d ollama neo4j
docker exec my_ollama ollama pull nomic-embed-text
docker exec my_ollama ollama pull qwen2.5-coder:7b
uv run run_pipeline.py --no-descriptions
```

For the full walkthrough — prerequisites, GPU setup, model selection, dry-run verification — see `docs/SETUP.md`.

---

## Function Embedding Pipeline

The pipeline scans a repository, embeds every function, stores nodes and similarity edges in Neo4j, and generates a report. It is a standalone subsystem under `src/pipeline/` and requires Neo4j and Ollama to be running.

```bash
# Full run — embeddings, descriptions, similarity graph, and report
uv run run_pipeline.py

# Skip LLM descriptions — much faster, code-embedding similarity only
uv run run_pipeline.py --no-descriptions

# Target a subfolder instead of the whole repo
uv run run_pipeline.py --path /path/to/repo/subdir --no-descriptions

# Validate extraction counts without touching Neo4j or Ollama
uv run run_pipeline.py --dry-run

# Generate a report from the current graph without re-running the pipeline
uv run run_pipeline.py --report-only
```

Reports are written to `run_reports/<repo_name>/<timestamp>/` as both a `.md` and a `.json` file. Runs are incremental — only changed functions are re-processed.

Full documentation: `docs/PIPELINE.md`

---

## Slack integration

The bot exposes `/pipeline`, `/report`, and `/query` slash commands and posts completion notifications with an attached report to a configured channel. Requires the `fastapi` container and Slack app credentials.

Setup instructions: `docs/SLACK_SETUP.md`

---

## Configuration

Two files are needed, both gitignored:

- `.env` — infrastructure settings (service URLs, credentials, Slack tokens). Copy from `.env.example`.
- `config.json` — application settings (repo paths, model names, pipeline tuning). Copy from `config.example.json`.

Full reference: `docs/CONFIG.md`

---

## Dependencies

Install all dependencies including dev and tool extras:

```bash
uv sync --all-extras
```

Runtime only:

```bash
uv sync
```

OS-level build prerequisites (Python headers, C toolchain) and the full declared dependency list: `docs/DEPENDENCIES.md`

---

## Repository Context Contract

The retrieval → coder context schema, validation rules, and prompt rendering format: `docs/CONTEXT_CONTRACT.md`

---

---

## Agent Workflow (On Hold — Unfinished)

> **This subsystem is not usable in its current state.** The LangGraph-based file-edit agent workflow is incomplete and has been put on hold. The sections below are retained for reference only.

### File-edit smoke test

Before running, create a local `config.json` from `config.example.json`. The `max_workflow_revision_cycles` field controls the maximum number of implement → validate → correct loops. `api_key` is optional and only needed for hosted providers.

```bash
uv run -m pytest -q
uv run -m scripts.test_file_edit
```

If a patch fails to apply, the tool falls back to a whole-file write and saves the failed diff under `.runtime/failed_patches/` for manual inspection.

### Observability

`run_monorepo_task` prints a human-readable execution trace to the console at the end of every run:

```bash
uv run -m scripts.run_monorepo_task --task "add docstrings to all public methods in foo.py"
```

A full per-run JSONL event log is written to `.runtime/runs/<run_id>.jsonl` and an aggregated JSON summary to `.runtime/runs/<run_id>.json`. Inspect the most recent run (requires `jq`):

```bash
ls -1 .runtime/runs/*.jsonl | tail -n1 | xargs cat | jq
```

### Scheduler stress demo

```bash
uv run -m scripts.stress_scheduler_fixture_repo --in-place
```
