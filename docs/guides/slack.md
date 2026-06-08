# Slack integration

The Slack bot exposes three slash commands and posts pipeline completion notifications with an attached report to a configured channel.

| Command | What it does |
|---|---|
| `/pipeline [flags]` | Triggers a full pipeline run. Accepts the same flags as the CLI (`--no-descriptions`, `--dry-run`, `--no-report`, `--path PATH`). |
| `/report` | Generates a report from the current graph without re-running the pipeline. |
| `/query [description]` | Searches the graph for functions semantically similar to the description. |

The bot runs inside the `fastapi` Docker container and communicates via Slack's Socket Mode — no public URL or inbound firewall rules are needed.

---

## Prerequisites

- A Slack workspace where you have permission to install apps.
- Services already running and the pipeline run at least once (from the [running the pipeline guide](running-the-pipeline.md)). The `/query` command searches the Neo4j graph — it returns no results if the graph is empty.
- `REPOS_ROOT` set in `.env` — the `fastapi` container mounts this path read-only so the pipeline can read source files when triggered via `/pipeline`.

---

## Step 1 — Create the Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**
2. Choose **From an app manifest**
3. Select your workspace and click **Next**
4. Replace the entire contents of the manifest editor with the following and click **Next**:

```json
{
    "display_information": {
        "name": "self-hosted LLM",
        "description": "Query your codebase using natural language",
        "background_color": "#1a1a2e"
    },
    "features": {
        "bot_user": {
            "display_name": "self-hosted LLM",
            "always_online": true
        },
        "slash_commands": [
            {
                "command": "/query",
                "description": "Search the codebase for semantically similar functions",
                "usage_hint": "[natural language description or function name]",
                "should_escape": false
            },
            {
                "command": "/pipeline",
                "description": "Trigger a full embedding pipeline run (report included by default)",
                "usage_hint": "[--no-descriptions] [--dry-run] [--no-report] [--path PATH]",
                "should_escape": false
            },
            {
                "command": "/report",
                "description": "Generate a similarity report from the current graph without re-running the pipeline",
                "usage_hint": "(no arguments)",
                "should_escape": false
            }
        ]
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "commands",
                "chat:write",
                "files:write"
            ]
        }
    },
    "settings": {
        "interactivity": {
            "is_enabled": true
        },
        "socket_mode_enabled": true
    }
}
```

5. Review the summary and click **Create**

---

## Step 2 — Generate the App-Level Token

This token opens the Socket Mode WebSocket connection.

1. In your app settings, go to **Basic Information → App-Level Tokens**
2. Click **Generate Token and Scopes**
3. Give it any name (e.g. `socket-token`)
4. Click **Add Scope** and select **`connections:write`**
   > The UI shows two scopes: `connections:write` and `app_configurations:write`. You need `connections:write`. Adding the other one will cause a `missing_scope` error at startup.
5. Click **Generate** and copy the token — it starts with `xapp-1-`
6. Add it to `.env`:
   ```
   SLACK_APP_TOKEN=xapp-1-...
   ```

---

## Step 3 — Install the app and get the Bot Token

1. Go to **Install App** in the left sidebar
2. Click **Install to Workspace** and authorise
3. Copy the **Bot User OAuth Token** — it starts with `xoxb-`
4. Add it to `.env`:
   ```
   SLACK_BOT_TOKEN=xoxb-...
   ```

---

## Step 4 — Start the full stack

```bash
docker compose up --build
```

Watch the `fastapi` container logs. A successful connection looks like:

```
INFO | Slack Socket Mode connected — slash commands are live
```

If you see `SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set`, check that both values are in `.env` and restart.

---

## Step 5 — Verify

Open any channel in your workspace and run:

```
/query find functions that handle authentication
```

You should see an ephemeral **Searching…** reply within a few seconds, followed by the results.

To trigger a pipeline run:

```
/pipeline --no-descriptions
```

Invalid flags return an ephemeral error with the usage hint.

---

## Completion notifications

To receive a notification when a pipeline run finishes, set `SLACK_NOTIFY_CHANNEL` in `.env` to a channel ID or `#name`:

```
SLACK_NOTIFY_CHANNEL=#deployments
```

Then invite the bot to that channel in Slack:

```
/invite @self-hosted LLM
```

Restart the stack to pick up the new env var:

```bash
docker compose up -d --build fastapi
```

On every pipeline run you will receive a Block Kit message:

```
✅ Pipeline complete

New/modified: 5
Unchanged: 441
Deleted: 2
Duration: 43s
```

On failure:

```
❌ Pipeline failed — ConnectionError: Neo4j unreachable
```

After every run (unless `--no-report` or `--dry-run`), a report summary is posted followed by the timestamped `.md` file as an attachment:

```
📊 monorepo — 2026-06-05 14:32 CEST

Functions 321   Edges 200   Density 0.62
Intra 97   Inter 103
Code ok 312   Failed 9   (8 overflow · 1 error)
Similarity >0.95: 12 · 0.90–0.95: 23 · 0.80–0.90: 165
8 duplication clusters
Largest: GamepadDriver.last_emitted — 5 functions, avg 0.963
🚨 HIGH_DUPLICATION_CLUSTER · CROSS_FILE_DUPLICATION · ARCHITECTURE_COUPLING
```

Leave `SLACK_NOTIFY_CHANNEL` unset to disable notifications entirely.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `missing_scope: needed connections:write` | App-Level Token has the wrong scope | Regenerate the token with `connections:write` (not `app_configurations:write`) |
| `SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set` | Tokens missing from `.env` | Add both tokens to `.env` and restart |
| `/query failed because the app did not respond` | Bot not connected or container not running | Check `docker logs fastapi` for errors |
| `not_allowed_token_type` | Wrong token type used | Use the App-Level Token (`xapp-`) for `SLACK_APP_TOKEN`, not the bot token |
| `not_in_channel` in fastapi logs | Bot not a member of `SLACK_NOTIFY_CHANNEL` | Open the channel in Slack and run `/invite @self-hosted LLM` |
| `missing_scope: needed files:write` | App installed before `files:write` scope was added | Add `files:write` to the manifest, then reinstall (**OAuth & Permissions → Reinstall App**) |
| Pipeline notification shows `New/modified: 0, Unchanged: 0` | Container cannot read the repo path | Set `REPOS_ROOT` in `.env` to the parent directory of your repos and restart |

---

→ Next: [Scheduled runs](scheduled-runs.md)
