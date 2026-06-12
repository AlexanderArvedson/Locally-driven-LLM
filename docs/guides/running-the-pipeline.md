# Running the pipeline

With services running and models pulled, you are ready to run the pipeline.

---

## Verify the setup first

Before a full run, confirm that all three pieces are in place:

**Neo4j** — open `http://localhost:7474` in a browser and log in with the credentials from `.env` (username `neo4j`, password as you set it). You should see an empty database.

**Ollama** — check that your pulled models are available:

```bash
curl http://localhost:11434/api/tags
```

You should see `nomic-embed-text` and `qwen2.5-coder:7b` (or your chosen models) in the response.

**Dry run** — extract functions and check Neo4j connectivity without writing anything or calling Ollama:

```bash
uv run run_pipeline.py --dry-run
```

This runs only the extraction and hash-check stages. It confirms the repo path is readable, tree-sitter can parse the files, and Neo4j accepts connections. Fix any errors reported here before continuing.

---

## First run

For your first run, skip LLM description generation. It produces richer similarity data but is slow, and it is easier to verify that everything works end-to-end first:

```bash
uv run run_pipeline.py --no-descriptions
```

As the pipeline runs, each of the 13 stages prints its name, count, and duration to stdout. A typical run on a medium-sized repo finishes in a few minutes with `--no-descriptions`.

On completion you will see a summary line and a timestamped report directory:

```
run_reports/<repo_name>/<timestamp>/
  <repo_name>_report_<timestamp>.md    — human-readable report
  <repo_name>_report_<timestamp>.json  — machine-readable export
```

The `.md` report contains embedding integrity stats, a similarity distribution histogram, top similar function pairs, duplication clusters, and heuristic flags. See [docs/PIPELINE.md](../PIPELINE.md) for the full report structure.

If `SLACK_NOTIFY_CHANNEL` is set, the report overview (Block Kit card) and the `.md` file are also posted to that channel automatically — the same as when triggered via the `/pipeline` Slack command.

---

## Subsequent runs are incremental

The pipeline tracks a SHA-256 hash of each function's source code. On each run:

- Functions whose source is unchanged are skipped for embedding and description.
- New or modified functions are fully re-processed.
- Functions that have disappeared from the repo are soft-deleted in Neo4j.

This means re-runs on large repos are fast unless many functions changed.

---

## Running with full descriptions

Once you have confirmed the basic run works, run without the `--no-descriptions` flag to generate LLM descriptions for each function. These improve similarity quality by adding a semantic signal on top of the raw code embeddings:

```bash
uv run run_pipeline.py
```

Description generation calls the chat model once per changed function, so this is significantly slower than a code-only run. For a repo with thousands of functions, expect the first full run to take tens of minutes.

---

## Other useful flags

| Flag | When to use it |
|---|---|
| `--report-only` | Generate a fresh report from the current graph without re-running the pipeline. |
| `--no-report` | Run the pipeline but skip report generation. |
| `--path PATH` | Override the repo path from config — useful for targeting a subfolder. |
| `--repo NAME` | Select a specific repository entry from `config.json` by name. |

The full flag reference and a description of every pipeline stage is in [docs/PIPELINE.md](../PIPELINE.md).

---

→ Next: [Slack integration](slack.md) (optional but recommended if you use slack)
