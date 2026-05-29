# Configuration Reference

Copy `config.example.json` to `config.json` and fill in the values for your setup.
`config.json` is gitignored and never committed.

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
| `max_iterations` | integer | Maximum number of LLM reasoning/coding iterations the agent may take before it is forced to stop and return its current result. Higher values allow more complex tasks but increase runtime and token usage. |

---

### `graph`

Controls the knowledge graph that the agent uses to understand the repository's structure.

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Graph construction strategy. `"hybrid"` combines AST-based parsing with embedding-based similarity. `"ast"` uses only AST parsing (faster, no embedding required). `"embedding"` uses only vector similarity (requires an embedding model). |
| `staleness_strategy` | string | How the system detects that the graph needs rebuilding. `"sha_based"` compares file content hashes — efficient and accurate. `"timestamp"` uses file modification times — faster but can produce false negatives. |
| `auto_update` | boolean | When `true` the graph is automatically rebuilt after the agent modifies files. Set to `false` to manage graph updates manually. |

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

Each key under `models` names a role the agent uses an LLM for. All four roles must be present; they may point to the same model if desired.

#### Common fields (all model entries)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Model identifier as recognised by the provider (e.g. `"llama3"`, `"qwen2.5-coder:7b"`, `"mistral"`). |
| `provider` | string | Provider backend. Use `"ollama"` for locally-run models, or the provider name for hosted APIs. |
| `api_key` | string \| null | API key for hosted providers. Set to `null` for local models that require no authentication. |
| `url` | string | Base URL of the model's API endpoint. For Ollama the default is `"http://localhost:11434"`. |

#### Roles

| Role key | Purpose |
|----------|---------|
| `chat` | General-purpose conversational model used for planning and task decomposition. |
| `coder` | Code generation model — should be a model fine-tuned for code (e.g. a Qwen-coder or DeepSeek-coder variant). |
| `reviewer` | Model used to review and critique generated code before a PR is opened. |
| `embedding` | Embedding model used to build the vector-similarity layer of the knowledge graph. Must produce dense vector outputs. |

---

### `integrations`

| Field | Type | Description |
|-------|------|-------------|
| `slack_webhook_url` | string \| null | Incoming Webhook URL for Slack notifications. The agent posts a summary message when a PR is created. Set to `null` to disable Slack notifications. |
