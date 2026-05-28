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

- Run the scheduler stress demo against the fixture repo and local model:

```bash
uv run -m scripts.stress_scheduler_fixture_repo --in-place
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

Dependencies
------------

The full set of declared runtime, test, and tooling dependencies is documented in:

- `docs/DEPENDENCIES.md`

That file also covers OS-level build prerequisites for native extensions, including the `Python.h` fix path.

If you want to install everything declared in `pyproject.toml`, use:

```bash
uv sync --all-extras
```