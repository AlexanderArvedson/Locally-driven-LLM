# Slack Setup Guide

This guide gets the **self-hosted LLM** Slack bot running from scratch.

---

## Prerequisites

- A Slack workspace where you have permission to install apps
- The system running via `docker compose up --build`

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
                "description": "Trigger a full embedding pipeline run",
                "should_escape": false
            }
        ]
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "commands",
                "chat:write"
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

This token is used to open the Socket Mode WebSocket connection.

1. In your app settings, go to **Basic Information → App-Level Tokens**
2. Click **Generate Token and Scopes**
3. Give it any name (e.g. `socket-token`)
4. Click **Add Scope** and select **`connections:write`**
   > ⚠️ The UI shows two scopes: `connections:write` and `app_configurations:write`. You need `connections:write`. The other one will cause a `missing_scope` error at startup.
5. Click **Generate** and copy the token — it starts with `xapp-1-`
6. Add it to your `.env`:
   ```
   SLACK_APP_TOKEN=xapp-1-...
   ```

---

## Step 3 — Install the app and get the Bot Token

1. Go to **Install App** in the left sidebar
2. Click **Install to Workspace** and authorise
3. Copy the **Bot User OAuth Token** — it starts with `xoxb-`
4. Add it to your `.env`:
   ```
   SLACK_BOT_TOKEN=xoxb-...
   ```

---

## Step 4 — Start the system

```bash
docker compose up --build
```

Watch the `fastapi` container logs. A successful Socket Mode connection looks like:

```
INFO | Slack Socket Mode connected — slash commands are live
```

If you see `SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set`, check that both values are present in `.env` and restart.

---

## Step 5 — Verify

Open any channel in your Slack workspace and run:

```
/query find functions that handle authentication
```

You should see an ephemeral **Searching…** reply within 3 seconds, followed by the results once the query completes.

To trigger a pipeline run:

```
/pipeline
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `missing_scope: needed connections:write` | App-Level Token has the wrong scope | Regenerate the token with `connections:write` (not `app_configurations:write`) |
| `SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set` | Tokens missing from `.env` | Add both tokens to `.env` and restart |
| `/query failed because the app did not respond` | Bot not connected or container not running | Check `docker logs fastapi` for errors |
| `not_allowed_token_type` | Wrong token type used | Make sure you're using the App-Level Token (`xapp-`) for `SLACK_APP_TOKEN`, not the bot token |
