# Locally-driven-LLM

A pipeline that scans a source repository, extracts every function and method, generates vector embeddings and LLM descriptions via Ollama, and builds a weighted similarity graph in Neo4j. Useful for code search, duplicate detection, and architectural analysis. Everything runs locally — no data leaves your machine.

---

## Quick start

```bash
cp .env.example .env                  # set NEO4J_PASSWORD, REPOS_ROOT, UID, GID
cp config.example.json config.json    # set name, url, base_branch, local_path
docker compose up -d ollama neo4j
docker exec my_ollama ollama pull nomic-embed-text
docker exec my_ollama ollama pull qwen2.5:7b
uv run run_pipeline.py --no-descriptions
```

For a complete walkthrough, start at [docs/guides/prerequisites.md](docs/guides/prerequisites.md).

---

## Two ways to run

**Standalone CLI** — `uv run run_pipeline.py`

Runs the embedding pipeline directly. Requires Neo4j and Ollama to be reachable but needs no FastAPI container, Slack setup, or scheduler. This is the right choice for one-off runs and local development.

**Full stack** — `docker compose up`

Starts all services including the `fastapi` container, which runs `main.py`. This enables Slack slash commands (`/pipeline`, `/query`, `/report`), the HTTP API, and cron-scheduled automatic runs. The pipeline is triggered via Slack or the API — `run_pipeline.py` is not used in this mode.

---

## Running the pipeline

```bash
uv run run_pipeline.py                      # full run with LLM descriptions
uv run run_pipeline.py --no-descriptions    # faster, code embeddings only
uv run run_pipeline.py --dry-run            # extract only, no writes
uv run run_pipeline.py --report-only        # report from current graph, no re-run
```

Reports are written to `run_reports/<repo_name>/<timestamp>/` as `.md` and `.json` files. Runs are incremental — only changed functions are re-processed.

---

## Reference

- [Pipeline reference](docs/PIPELINE.md) — all 13 stages, CLI flags, graph schema, report sections, example Cypher queries
- [Configuration reference](docs/CONFIG.md) — every `.env` and `config.json` field with types and defaults
- [Dependencies](docs/DEPENDENCIES.md) — install instructions, system prerequisites, and full dependency list

---

## Setup guides

Step-by-step guides for getting everything running:

1. [Prerequisites](docs/guides/prerequisites.md) — Docker, uv
2. [Configuration](docs/guides/configuration.md) — `.env` and `config.json`
3. [Starting services](docs/guides/services.md) — Ollama, Neo4j, GPU setup
4. [Pulling models](docs/guides/models.md) — embedding and chat models
5. [Running the pipeline](docs/guides/running-the-pipeline.md) — dry run, first run, flags
6. [Slack integration](docs/guides/slack.md) — slash commands, notifications *(optional)*
7. [Scheduled runs](docs/guides/scheduled-runs.md) — cron schedule *(optional)*

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

`run_monorepo_task` prints a human-readable execution trace at the end of every run:

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
