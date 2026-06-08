# Setup Guide

This guide takes you from a fresh clone to a working pipeline run.

---

## What you are setting up

The pipeline depends on three services:

- **Ollama** — runs LLM inference and embedding generation locally. All model calls stay on your machine.
- **Neo4j** — graph database that stores function nodes, embeddings, and similarity edges.
- **FastAPI app** — hosts the Slack bot and cron scheduler. Only needed if you want Slack commands or automatic scheduled runs. Not required for CLI use.

### Two running modes

**Local mode** (recommended for getting started): `uv run run_pipeline.py` runs on your machine and connects to Ollama and Neo4j at `localhost`. The `.env` defaults from `.env.example` work as-is.

**Docker mode**: Slack slash commands and scheduled runs go through the `fastapi` container, which runs the pipeline inside Docker. `docker-compose.yml` overrides the service URLs automatically (`bolt://neo4j:7687`, `http://ollama:11434`) — you do not need to change `.env` for this.

Start with local mode. Add the `fastapi` container only when you need Slack or cron.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2 (for the infrastructure services)
- [uv](https://github.com/astral-sh/uv) (for running the pipeline CLI locally)

---

## Step 1 — Copy and edit config files

```bash
cp .env.example .env
cp config.example.json config.json
```

**Edit `.env`:**

| Variable | What to set |
|---|---|
| `NEO4J_PASSWORD` | Any password — must match what the container is started with |
| `REPOS_ROOT` | Absolute path to the **parent** directory of your target repo. If your repo is at `/home/alice/projects/myrepo`, set this to `/home/alice/projects`. |

Leave `SLACK_*` variables as-is for now; they are only needed in Step 6.

**Edit `config.json`:**

Under `repositories[0]`:

| Field | What to set |
|---|---|
| `name` | A short identifier for your repo (e.g. `"myrepo"`) — used in report filenames and Slack messages |
| `local_path` | Absolute path to the repo on disk (e.g. `"/home/alice/projects/myrepo"`) — must be under `REPOS_ROOT` |

Leave all other fields at their defaults for now. See `docs/CONFIG.md` for the full field reference.

---

## Step 2 — Start infrastructure services

```bash
docker compose up -d ollama neo4j
```

This starts Ollama and Neo4j only. The `fastapi` container is not needed for CLI use.

**If you have an Nvidia GPU**, use the GPU override to enable hardware acceleration:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d ollama neo4j
```

This requires the [Nvidia Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html). Without it, the override file will cause Compose to fail. The base `docker-compose.yml` runs on any machine without modification — GPU acceleration is opt-in.

**If using an external Neo4j instance** (not the bundled container): ensure the APOC plugin is installed. The pipeline's schema stage uses APOC procedures. The bundled `neo4j` container installs APOC automatically.

---

## Step 3 — Pull Ollama models

The pipeline needs two types of model configured in `config.json`:

- **Embedding model** (`models.embedding`) — produces fixed-dimension vectors for similarity search. Must be a dedicated embedding model.
- **Chat/coder models** (`models.chat`, `models.coder`, `models.describer`, `models.semantic_validator`) — used for LLM description generation and code tasks. Can all point to the same model.

The defaults in `config.example.json` are `nomic-embed-text` (embedding) and `qwen2.5-coder:7b` (everything else).

**If Ollama is running inside Docker (the default after Step 2):**

```bash
docker exec my_ollama ollama pull nomic-embed-text
docker exec my_ollama ollama pull qwen2.5-coder:7b
```

**If Ollama is running on your machine directly (not via Docker):**

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5-coder:7b
```

### Finding other models

Browse [ollama.com/library](https://ollama.com/library):

- For `models.embedding`: filter by the **Embedding** tag. `nomic-embed-text` and `mxbai-embed-large` are common choices.
- For chat/coder roles: any capable instruction-tuned model works. `qwen2.5-coder` variants are a good default for code-heavy tasks; `llama3` and `mistral` are general-purpose alternatives.

> **Important**: Do not use a chat model for `models.embedding`. Chat models do not produce the fixed-dimension dense vectors the pipeline expects — Ollama will return an error. Always use a model listed under the Embedding tag for that role.

---

## Step 4 — Verify the setup

Before running the full pipeline, confirm all services are reachable:

**Neo4j browser** — open `http://localhost:7474` and log in with the username `neo4j` and the password you set in `.env`. You should see an empty database.

**Ollama models** — check that your pulled models are available:

```bash
curl http://localhost:11434/api/tags
```

You should see `nomic-embed-text` and `qwen2.5-coder:7b` (or whichever models you pulled) listed in the response.

**Dry run** — extract functions and validate Neo4j connectivity without writing anything:

```bash
uv run run_pipeline.py --dry-run
```

This runs the extraction and hash-check stages only — no Ollama calls, no Neo4j writes. It confirms the repo path is readable, tree-sitter can parse the files, and the function count looks reasonable. If this fails, fix the issue before proceeding.

---

## Step 5 — First pipeline run

```bash
# Recommended for the first run — skips LLM descriptions, much faster
uv run run_pipeline.py --no-descriptions
```

What to expect:

- The 13 pipeline stages print to stdout with counts and timing as each completes.
- On completion, a timestamped report directory is created at `run_reports/<repo_name>/<timestamp>/` containing a human-readable `.md` report and a machine-readable `.json` export.
- Subsequent runs are incremental — only functions whose source has changed are re-embedded and re-described. Unchanged functions are skipped.

Once you are satisfied with the embedding results, run with full LLM descriptions:

```bash
uv run run_pipeline.py
```

See `docs/PIPELINE.md` for all CLI flags and a full explanation of every pipeline stage and report section.

---

## Step 6 (optional) — Slack integration

The bot exposes `/pipeline`, `/report`, and `/query` slash commands and posts completion notifications to a channel.

Full setup instructions: `docs/SLACK_SETUP.md`

At a minimum you will need to:

1. Create a Slack app and generate `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` — both explained in `docs/SLACK_SETUP.md`.
2. Add them to `.env`, along with `SLACK_NOTIFY_CHANNEL`.
3. Start the full stack (including the `fastapi` container):

```bash
docker compose up --build
```

`REPOS_ROOT` must be set in `.env` — the `fastapi` container mounts this path read-only so the pipeline can read source files.

---

## Step 7 (optional) — Scheduled automatic runs

The `cron` field at the top of `config.json` controls when the pipeline runs automatically. The default (`"0 0 * * *"`) fires once daily at midnight.

On each scheduled fire, the FastAPI server enqueues a pipeline run and posts a completion notification + report to `SLACK_NOTIFY_CHANNEL`. This only works when the `fastapi` container is running.

To disable scheduled runs, set `cron` to a never-firing expression:

```json
"cron": "0 0 31 2 *"
```

Or simply leave `SLACK_NOTIFY_CHANNEL` unset in `.env` if you want the run to happen silently without Slack output.
