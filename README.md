# Locally-driven-langgraph-LLM

Quick notes (how to run the file-edit MVP):

- Run unit tests:

```bash
python3 -m unittest -q
```

- Run the single-file edit smoke test as a local integration check (uses `sandbox/example.py`):

```bash
uv run -m scripts.test_file_edit
```

If a patch fails to apply the tool will save artifacts under `.runtime/failed_patches/` for manual inspection.

Observability
-------------

Run the file-edit smoke path to generate a per-run JSONL trace under `.runtime/runs/`:

```bash
uv run -m scripts.test_file_edit
```

Inspect the most recent run (requires `jq`):

```bash
ls -1 .runtime/runs | tail -n1 | xargs -I{} sh -c 'cat .runtime/runs/{} | jq'
```

Logs and runtime artifacts are ignored by git; see `.gitignore` for entries such as `.runtime/`.

Repository Context Contract
---------------------------

The retrieval -> coder repository context schema, validation rules, and
prompt rendering format are documented in:

- `docs/CONTEXT_CONTRACT.md`

Runtime Lifecycle
-----------------

The scheduler, registry, queue, and cancellation semantics are documented in:

- `docs/RUNTIME_LIFECYCLE.md`