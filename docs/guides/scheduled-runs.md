# Scheduled runs

The pipeline can run automatically on a cron schedule. On each fire, the FastAPI server enqueues a pipeline run and posts a notification to `SLACK_NOTIFY_CHANNEL` when it starts, followed by the standard completion notification and report when it finishes.

The start notification shows the repo, cron expression, and UTC time so it is always clear what triggered the run:

```
⏰ Scheduled pipeline run queued for *monorepo* — `0 0 * * *` — 2026-06-06 00:00 UTC
```

Scheduled runs require the `fastapi` container to be running and Slack to be configured. If you have not done that yet, see the [Slack guide](slack.md) first.

---

## Configuring the schedule

The `cron` field at the top of `config.json` controls when the pipeline fires. It uses standard five-part cron syntax (`minute hour day month weekday`).

The default fires once daily at midnight:

```json
"cron": "0 0 * * *"
```

Some examples:

| Expression | Schedule |
|---|---|
| `"0 0 * * *"` | Daily at midnight |
| `"0 3 * * 1"` | Every Monday at 03:00 |
| `"0 */6 * * *"` | Every 6 hours |
| `"30 8 * * 1-5"` | Weekdays at 08:30 |

Changes to `cron` require a container restart to take effect:

```bash
docker compose up -d --build fastapi
```

---

## Disabling scheduled runs

Set `cron` to a never-firing expression:

```json
"cron": "0 0 31 2 *"
```

February 31st never occurs, so this expression is safe to use as a "disabled" sentinel.

Alternatively, leave `SLACK_NOTIFY_CHANNEL` unset in `.env`. The scheduled run will still fire, but no notification or report will be posted.

---

← Previous: [Slack integration](slack.md)
