# Configuration

Two files control the system, both gitignored and never committed. Copy the examples and fill in the values for your environment.

```bash
cp .env.example .env
cp config.example.json config.json
```

---

## `.env` — infrastructure settings

`.env` holds service endpoints, credentials, and Docker tuning. Docker Compose reads it automatically.

Open `.env` and set these two values:

| Variable | What to set |
|---|---|
| `NEO4J_PASSWORD` | Any password you choose — used both to initialise the Neo4j container and to connect to it. |
| `REPOS_ROOT` | Absolute path to the **parent** directory of your target repo. If your repo is at `/home/alice/projects/myrepo`, set this to `/home/alice/projects`. The container mounts this path to read source files. |

Leave the Ollama variables at their defaults. Leave the `SLACK_*` variables blank for now — they are only needed if you set up Slack later.

---

## `config.json` — application settings

`config.json` holds repository paths, model names, and pipeline tuning. It contains no secrets.

Open `config.json` and fill in the `repositories[0]` entry:

| Field | What to set |
|---|---|
| `name` | A short identifier for your repo (e.g. `"myrepo"`). Used in report filenames and log output. |
| `local_path` | Absolute path to the repo on disk (e.g. `"/home/alice/projects/myrepo"`). Must be under `REPOS_ROOT`. |

The model names default to `nomic-embed-text` (embedding) and `qwen2.5-coder:7b` (chat/coder). These match what you will pull in the [Models](models.md) guide — leave them as-is for now.

**If your repo contains TypeScript or JavaScript**, add the relevant languages to `pipeline.supported_languages`. The default only scans Python files:

```json
"pipeline": {
  "supported_languages": ["python", "typescript", "javascript"]
}
```

Supported values are `"python"`, `"typescript"`, and `"javascript"`. Files with unlisted extensions are silently skipped, so a TypeScript repo on the default setting will extract zero functions.

**`integrations.slack_webhook_url`** — this field is for the agent workflow (on hold) and has no effect on the pipeline. Leave it `null`.

Everything else can stay at the defaults for a first run. The full field reference is in [docs/CONFIG.md](../CONFIG.md).

---

→ Next: [Starting services](services.md)
