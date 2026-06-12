# Configuration

Two files control the system, both gitignored and never committed. Copy the examples and fill in the values for your environment.

```bash
cp .env.example .env
cp config.example.json config.json
```

---

## `.env` — infrastructure settings

`.env` holds service endpoints, credentials, and Docker tuning. Docker Compose reads it automatically.

Open `.env` and set these values:

| Variable | What to set |
|---|---|
| `NEO4J_URI` | Leave as `bolt://localhost:7687` (the default). `docker-compose.yml` always injects `bolt://neo4j:7687` into the container for Docker runs — you never need to change this value for the full stack. |
| `NEO4J_PASSWORD` | Any password you choose — used both to initialise the Neo4j container and to connect to it. |
| `REPOS_ROOT` | Absolute path to the **parent** directory of your target repo. If your repo is at `/home/alice/projects/myrepo`, set this to `/home/alice/projects`. The container mounts this path read-write so the pipeline can clone the repo on first run and pull updates on subsequent runs. |
| `FASTAPI_PORT` | Only change this if port `8000` is already in use on your machine. Defaults to `8000`. |
| `UID` | Your host user ID. Run `id -u` to find it. The fastapi container runs as this user so files written to `run_reports/` are owned by you and deletable without `sudo`. |
| `GID` | Your host group ID. Run `id -g` to find it. |

Leave `OLLAMA_URL` at its default (`http://localhost:11434`) — `docker-compose.yml` always overrides it to the Docker-internal name when running the full stack. Leave the `SLACK_*` variables blank for now — they are only needed if you set up Slack later.

---

## `config.json` — application settings

`config.json` holds repository paths, model names, and pipeline tuning. It contains no secrets.

Open `config.json` and fill in the `repositories[0]` entry:

| Field | What to set |
|---|---|
| `name` | A short identifier for your repo (e.g. `"myrepo"`). Used in report filenames and log output. |
| `url` | HTTPS git URL of the repository (e.g. `"https://github.com/owner/repo.git"`). Used to clone the repo automatically on first run. |
| `base_branch` | The main branch of the repo (e.g. `"main"` or `"develop"`). The pipeline checks out and pulls this branch before each run. |
| `local_path` | Absolute path where the repo should be cloned on disk (e.g. `"/home/alice/projects/myrepo"`). Must be under `REPOS_ROOT`. Created automatically if it does not exist. |

**`credentials.git.token`** — leave this empty if your repository is public. Set it to a GitHub Personal Access Token if the repository is private (requires `Contents: read` scope) or if you plan to use the agent workflow to push branches and open pull requests (requires `Contents: write` and `Pull requests: write` as well). The token is only used for git operations — the pipeline itself never needs it for a public repo.

The model names default to `nomic-embed-text` (embedding) and `qwen2.5-coder:7b` (chat/coder). These match what you will pull in the [Models](models.md) guide — leave them as-is for now.

The example config already includes `"python"` and `"typescript"`. If your repo also contains JavaScript, add it:

```json
"pipeline": {
  "supported_languages": ["python", "typescript", "javascript"]
}
```

Supported values are `"python"`, `"typescript"`, and `"javascript"`. Files with unlisted extensions are silently skipped — remove any languages your repo does not use to avoid scanning noise.

A few defaults worth knowing before your first run:

- **`pipeline.limits.min_loc_threshold`** defaults to `3` in `config.example.json` (disabled with `0` in code). Functions shorter than this many lines are silently skipped before embedding and never stored in Neo4j. If short utility functions are missing from your graph, check this value.
- **`pipeline.checkpoint.enabled`** defaults to `true`. After every 10 descriptions the pipeline saves progress to `.pipeline_checkpoints/`. If a run crashes, the next run resumes from the checkpoint automatically rather than starting over.

Everything else can stay at the defaults for a first run. The full field reference is in [docs/CONFIG.md](../CONFIG.md).

---

← Previous: [Prerequisites](prerequisites.md) | → Next: [Starting services](services.md)
