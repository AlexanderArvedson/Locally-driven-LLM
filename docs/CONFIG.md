# Configuration Reference

## Setup

**Application config** — copy `config.example.json` to `config.json` and fill in the values for your setup. `config.json` is gitignored and never committed.

**Docker / Ollama server config** — copy `.env.example` to `.env` and adjust the values as needed. `.env` is gitignored and read automatically by Docker Compose for `${VAR}` substitution in `docker-compose.yml`. The two variables it controls are:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_KEEP_ALIVE` | `60m` | How long Ollama keeps a loaded model in VRAM after the last request. Accepts duration strings (`60m`, `24h`), `0` (never unload), or `-1` (unload immediately after each request). |
| `OLLAMA_NUM_PARALLEL` | `1` | Maximum number of requests the Ollama server handles concurrently. Higher values increase throughput at the cost of additional VRAM per slot. |

After editing `.env`, apply the changes with `docker compose up --build`.

---

## Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `cron` | string | Cron expression controlling how often the automated workflow runs. Uses standard 5-part cron syntax (`minute hour day month weekday`). Default `"0 0 * * *"` runs once daily at midnight. |

---

## `system`

Global settings that apply across all repositories.

| Field | Type | Description |
|-------|------|-------------|
| `context_path` | string | Directory where the system stores its persistent context (run history, memory, etc.). Supports `~` expansion. |

---

## `repositories[]`

A list of repository configurations. Each entry describes one target repository the agent can operate on.

### Identity

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable name for the repository. Used in logs and PR descriptions. |
| `url` | string | Remote Git URL (HTTPS). Used when cloning a missing repository and when constructing authenticated push URLs. |
| `base_branch` | string | The branch the agent checks out as its base before creating task branches (e.g. `"main"` or `"develop"`). |
| `prefix` | string | Prefix applied to all agent-created branch names. The workflow appends a date and task slug, e.g. `AI-2026-05-29-add-type-hints`. |
| `local_path` | string | Absolute path to the local clone on disk. If the directory does not exist the agent will clone the repository automatically. |

### Timestamps

Managed automatically by the system. Set both to `null` when adding a new repository entry.

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | string \| null | ISO 8601 timestamp written the first time the agent runs against this repository. |
| `updated_at` | string \| null | ISO 8601 timestamp updated on every successful agent run. |

### Execution

| Field | Type | Description |
|-------|------|-------------|
| `max_workflow_revision_cycles` | integer (≥ 1) | Maximum number of complete implement → validate → correct loops the workflow may run before it is forced to stop and return its current result. Higher values allow more complex tasks but increase runtime and token usage. |
| `semantic_threshold` | float | Minimum *effective score* (0.0–1.0) the semantic validator must produce before the pipeline proceeds to write the file. Default `0.75`. The effective score is `task_alignment_score` minus a penalty for high `regression_risk` (risk above 0.4 is penalised at 0.5× the excess). Lower values are more permissive; raise toward `1.0` for stricter intent checking. |

---

### `graph`

Controls the knowledge graph that the agent uses to understand the repository's structure.

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Graph storage strategy. `"hybrid"` checks the repository's own `.graphify/` directory first, then falls back to the system-managed store, building if neither is present. `"system"` always uses the system-managed store (under `system.context_path/graphs/`). `"repo_local"` uses only `.graphify/` inside the repository — raises an error if none is present. |
| `auto_update` | boolean | When `true` the graph is automatically built or rebuilt in system/hybrid mode whenever the current git HEAD has no matching graph. Set to `false` to manage graph updates manually (an error is raised if no valid graph exists). |

Graph freshness is determined exclusively by comparing the git HEAD SHA at run time against the SHA recorded in `graph_meta.json` alongside each `graph.json`. Timestamps are never used.

---

### `retrieval`

Controls how many files and tokens the retrieval pipeline assembles into the LLM context window. All fields have defaults so the block may be omitted.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_context_files` | integer (> 0) | `20` | Maximum number of files the retrieval pipeline may include in the assembled context. Files are added in descending relevance order until this cap or the token budget is reached, whichever comes first. |
| `max_context_tokens` | integer (> 0) | `12000` | Maximum estimated token count of the assembled retrieval context. The token count is estimated using `TokenCounter` before inference so the LLM never receives more context than this budget allows. |
| `limit_reached_behavior` | string | `"warn"` | Action taken when either retrieval limit is hit. `"ignore"` silently truncates. `"warn"` logs a warning and continues. `"fail"` aborts retrieval with a `RuntimeError`, causing the workflow run to fail. |

#### Retrieval statistics

When a limit is hit the system logs statistics including candidate count, selected count, and token budget used. These are always included in the `emit_success` payload for the `retrieval_node`.

---

### `planner`

Controls the file-selection step that runs after retrieval. When a task is submitted without an explicit `--target-file`, the planner asks the LLM to choose which files from the retrieval candidates actually need to be modified. The block may be omitted; all fields have defaults.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_files` | integer (1–10) | `3` | Maximum number of files the planner may select for modification in a single run. The LLM is prompted with this limit; its response is also hard-capped to this value after parsing. Raise for tasks that inherently touch multiple files; lower to keep changes tightly scoped. |

#### Planner behaviour

- When `--target-file` is provided the planner is skipped entirely and the supplied path is used directly.
- When no target is specified the planner receives the ranked list from `retrieval` and makes an LLM call to select 1–`max_files` files to modify.
- If the LLM returns an empty selection, or all selected paths are not in the retrieval candidates (hallucinations are filtered out), the run terminates with a `planner_error` and no files are written.

---

### `credentials`

Authentication used when cloning or pushing to the remote repository.

#### `credentials.git`

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | Git hosting username (e.g. your GitHub username). Used to construct the authenticated remote URL. |
| `token` | string | Personal access token with at least `repo` scope. Never commit this value — keep it in `config.json` which is gitignored. |

---

### `models`

Each key under `models` names a role the agent uses an LLM for. All four roles must be present; they may point to the same model if desired. All model entries share the same field schema.

#### Common fields (all model entries)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — | Model identifier as recognised by the provider (e.g. `"llama3"`, `"qwen2.5-coder:7b"`, `"mistral"`). |
| `provider` | string | — | Provider backend. Use `"ollama"` for locally-run models, or the provider name for hosted APIs (e.g. `"openai"`). |
| `api_key` | string \| null | `null` | API key for hosted providers. Set to `null` for local models that require no authentication. |
| `url` | string | — | Base URL of the model's API endpoint. For Ollama the default is `"http://localhost:11434"`. |
| `temperature` | number \| null | `null` | Sampling temperature passed to the provider. When `null` the parameter is omitted from the request and the model uses its own default. Must be ≥ 0 when non-null. |
| `max_tokens` | integer \| null | `null` | Maximum tokens the model may generate per request. When `null` the parameter is omitted. Must be > 0 when non-null. For Ollama this maps to `num_predict`. |
| `num_ctx` | integer \| null | `null` | Per-request context window size passed to Ollama as `num_ctx`. Overrides the model's compiled default for that request. When `null` the parameter is omitted. Must be > 0 when non-null. Has no effect for non-Ollama providers. |
| `timeout_seconds` | integer (> 0) | `300` | Per-request wall-clock timeout in seconds. The request is cancelled and an error is raised if the model does not respond within this duration. |
| `allow_gpu` | boolean | `true` | When `true`, Ollama offloads all model layers to the GPU (`num_gpu=-1`). When `false`, inference runs on CPU only (`num_gpu=0`). Ollama gracefully falls back to CPU if no compatible GPU is found, so `true` is safe on CPU-only hosts. |

#### Roles

| Role key | Purpose |
|----------|---------|
| `chat` | General-purpose conversational model used for planning and task decomposition. |
| `coder` | Code generation model — should be a model fine-tuned for code (e.g. a Qwen-coder or DeepSeek-coder variant). |
| `semantic_validator` | Model used to judge whether generated code satisfies the original task intent. Receives the task description, a unified diff of the change, and a truncated original file snippet for context; returns a structured JSON evaluation including `task_alignment_score` and `regression_risk`. Can be the same model as `coder`. |
| `embedding` | Embedding model used to build the vector-similarity layer of the knowledge graph. Must produce dense vector outputs. |

---

### `integrations`

| Field | Type | Description |
|-------|------|-------------|
| `slack_webhook_url` | string \| null | Incoming Webhook URL for Slack notifications. The agent posts a summary message when a PR is created. Set to `null` to disable Slack notifications. |
