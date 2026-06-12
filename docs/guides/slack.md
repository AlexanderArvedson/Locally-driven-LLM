# Slack integration

The Slack bot exposes three slash commands and posts pipeline completion notifications with an attached report to a configured channel.

| Command | What it does |
|---|---|
| `/pipeline [flags]` | Triggers a full pipeline run. Accepts the same flags as the CLI (`--no-descriptions`, `--dry-run`, `--no-report`, `--path PATH`). |
| `/report` | Generates a report from the current graph without re-running the pipeline. |
| `/query [description]` | Searches the graph for functions semantically similar to the description. |

The bot runs inside the `fastapi` Docker container and communicates via Slack's Socket Mode — no public URL or inbound firewall rules are needed.

**Which repository is targeted:** all three commands always operate on the **first repository** entry in `config.json`. There is no `--repo` flag for Slack commands — to target a different repository, reorder the `repositories` array in `config.json` and restart the container.

---

## Prerequisites

- A Slack workspace where you have permission to install apps.
- Services already running and the pipeline run at least once (from the [running the pipeline guide](running-the-pipeline.md)). The `/query` command searches the Neo4j graph — it returns no results if the graph is empty.
- `REPOS_ROOT` set in `.env` — the `fastapi` container mounts this path read-write so the pipeline can clone and pull the repo when triggered via `/pipeline`.

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
        "description": "Search your codebase by describing function behaviour",
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
                "usage_hint": "[describe the behaviour — e.g. AES encrypt decrypt value]",
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

You should see an ephemeral **Searching…** reply within a few seconds, followed by the results. Each result shows the function name, similarity score out of 1.0, file path, and — when descriptions are populated — a short italic summary of what the function does:

```
Results for: "find functions that handle authentication"

• `AuthMiddleware.authenticate`  ·  score 0.91 / 1.0  ·  middleware/auth.ts
  _Middleware that validates JWT tokens on protected routes and rejects unauthenticated requests._
• `JwtHelper.verify`  ·  score 0.87 / 1.0  ·  service/jwtHelper.ts
  _Verifies a JWT token signature and returns the decoded payload._
```

To trigger a pipeline run:

```
/pipeline --no-descriptions
```

Invalid flags return an ephemeral error with the usage hint.

---

## Writing effective queries

`/query` embeds your text with the same model used by the pipeline and finds functions whose code or description embeddings are closest to your query vector. This means **vocabulary matters** — the query works best when you describe the *behaviour* you are looking for rather than asking a navigational question.

**Prefer descriptive over navigational:**

| Less effective | More effective |
|---|---|
| `/query where is crypto handled?` | `/query AES encrypt decrypt value` |
| `/query authentication` | `/query verify JWT token from request header` |
| `/query database stuff` | `/query Sequelize query with where clause and include` |

**Why this matters:** a query like "where is crypto handled?" embeds close to RSA/JWT concepts (the dominant meaning of "crypto" in web services) rather than AES symmetric encryption — even if the `Crypto` class is exactly what you want. Describing the operation directly avoids this ambiguity.

**Tips:**
- Use the same terminology the code likely uses — function names, library names, error messages, type names
- Describe inputs, outputs, or side effects rather than asking "where is X?"
- Short, specific phrases (3–8 words) tend to score better than full sentences
- If descriptions are populated in the graph, abstract intent ("validate deadline has not passed") works well alongside structural queries ("compare two date timestamps")

---

## Pipeline progress notifications

When `SLACK_NOTIFY_CHANNEL` is set, the pipeline posts a live running commentary to Slack in a thread — one message per stage, plus periodic progress updates during long-running stages. This lets you monitor execution without access to server logs.

To enable, set `SLACK_NOTIFY_CHANNEL` in `.env` to a channel ID or `#name`:

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

### Thread strategy

When the pipeline starts, one message is posted to the channel as the thread anchor. All stage updates and progress reports are posted as replies in that thread — the channel stays clean while the full trace is one click away. When the pipeline finishes, the original channel message is updated to show the final outcome.

### Stage notifications

Each pipeline stage posts a Block Kit card with a header, divider, and stats body. The content of each card:

```
Repository synchronisation completed.
───────────────────────────────────
Status: Already up to date
Operation: Pull
Branch: main
Commit: a1b2c3d
```

```
Function extraction completed.
───────────────────────────────────
Files processed: 1,284
Functions extracted: 34,821
Duration: 3m 12s
```

```
Code embeddings completed.
───────────────────────────────────
Generated embeddings: 34,821
Duration: 42m 15s
```

`Failures` only appears when there are failures. If the run resumes from a checkpoint, an `Already completed` line appears first showing how many records were skipped:

```
Code embeddings completed.
───────────────────────────────────
Already completed: 34,821
Generated embeddings: 0
Duration: 0s
```

```
Similarity analysis completed.
───────────────────────────────────
Relationships created: 87,421
Duration: 8m 03s
```

### Progress updates

During code embedding, description generation, and description embedding, progress is reported every configured number of items:

```
Code embedding progress
───────────────────────────────────
Processed: 12,000 / 34,821
Progress: 34.5%
Rate: 142 items/sec
Elapsed: 1h 12m
ETA: 2h 41m remaining
```

### Pipeline completion

The thread anchor message is updated to show a one-line outcome:

```
✅ Pipeline complete — 5,241 changed, 42m 15s
```

A Block Kit card is also posted to the thread with the full run summary:

```
✅ Pipeline complete
─────────────────────────────────
New/modified: 5,241
Unchanged: 18,302
Deleted: 12
Duration: 42m 15s
Excluded by LOC threshold: 116    ← only shown when loc_filtered > 0
```

On failure:

```
❌ Pipeline failed — ConnectionError: Neo4j unreachable
```

### Configuration

Progress notifications are controlled by a `slack` block inside the `pipeline` section of `config.json`:

```json
"pipeline": {
  "slack": {
    "enabled": true,
    "debug_messages": false,
    "embed_progress_interval": 100,
    "describe_progress_interval": 10
  }
}
```

| Field | Default | Purpose |
|---|---|---|
| `enabled` | `true` | Enables or disables all pipeline progress notifications. |
| `debug_messages` | `false` | When `true`, also posts operational detail such as "Repository found — pulling latest changes…" |
| `embed_progress_interval` | `100` | Items between progress posts during code and description embedding (fast stages, sub-second/item). |
| `describe_progress_interval` | `10` | Items between progress posts during description generation (slow stage, 30–120 s/item). |

Setting `enabled` to `false` or leaving `SLACK_NOTIFY_CHANNEL` unset disables all pipeline notifications.

---

## Completion notifications

After every pipeline run — whether triggered via the `/pipeline` Slack command or run directly with `run_pipeline.py` — a report summary is posted to `SLACK_NOTIFY_CHANNEL` followed by the timestamped `.md` file as an attachment. The push notification preview shows a one-line health verdict, e.g.:

```
✅ Report (monorepo) — 2 flags raised, 321 functions
```

The full Block Kit message contains the following sections, each separated by a divider:

```
📊 monorepo — 2026-06-05 14:32 CEST

Summary
321 functions indexed across TypeScript. 2 concerns detected.
Duplication is the dominant concern: cluster 1 groups 5 functions
across 3 file(s) — primary consolidation target is `GamepadDriver.last_emitted`.

Graph
Functions: 321
Edges: 200
Density: 0.62 (how connected functions are on average)
Intra-file: 97 (similar functions in the same file)
Cross-file: 103 (similar functions across different files)
Isolated: 4 (no similar counterparts found)

Embedding
Code — OK: 312 · Chunked: 8 · Failed: 1
Descriptions — OK: 305 · Failed: 3

Similarity
>0.95 (near-identical): 12 (3.7%)
0.90–0.95 (highly similar): 23 (7.2%)
0.80–0.90 (similar): 165 (51.4%)
≤0.80 (low similarity): 44 (13.7%)

Duplication clusters: 8
• GamepadDriver.last_emitted  ·  5 functions, avg similarity 0.963
• KeyboardDriver.process  ·  3 functions, avg similarity 0.941
• AuthMiddleware.validate  ·  3 functions, avg similarity 0.921

Flags
🚨 High duplication — large groups of near-identical functions
🚨 Cross-file duplication — same logic copied across multiple files

Top pairs
• KeyboardDriver.last_emitted ↔ WindowsGamepadDriver.last_emitted  ·  1.0000
• GamepadDriver.emit ↔ XboxDriver.emit  ·  0.9971
• AuthService.validate ↔ AuthMiddleware.check  ·  0.9943
```

When no flags are raised the Flags section shows `✅ No flags raised` instead.

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
