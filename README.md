# Locally-driven-langgraph-LLM

Quick notes (how to run the file-edit MVP):

- Run unit tests:

```bash
python3 -m unittest -q
```

- Run the single-file edit smoke test (uses `sandbox/example.py`):

```bash
uv run -m scripts.test_file_edit
```

If a patch fails to apply the tool will save artifacts under `failed_patches/` for manual inspection.

Observability
-------------

Run the file-edit smoke path to generate a per-run JSONL trace under `logs/runs/`:

```bash
uv run -m scripts.test_file_edit
```

Inspect the most recent run (requires `jq`):

```bash
ls -1 logs/runs | tail -n1 | xargs -I{} sh -c 'cat logs/runs/{} | jq'
```

Logs and runtime artifacts are ignored by git; see `.gitignore` for entries such as `logs/runs/` and `failed_patches/`.