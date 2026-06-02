# Locally-driven-langgraph-LLM

Quick notes (how to run the file-edit MVP):

Before running the app, create a local `config.json` from `config.example.json` and edit the values for your machine and model setup. The repository ignores `config.json`, so each checkout can keep its own runtime settings. The example file is just a template; the local file is where the real repo-specific values live. The `max_workflow_revision_cycles` field under each repository controls the maximum number of implement → validate → correct loops the workflow may run. `api_key` is optional and is only needed for hosted providers; leave it `null` when using local hosting such as Ollama.

```bash
cp config.example.json config.json
```

- Run unit tests:

```bash
uv run -m pytest -q
```

- Run the single-file edit smoke test as a local integration check (uses `sandbox/example.py`):

```bash
uv run -m scripts.test_file_edit
```

- Run the scheduler stress demo against the fixture repo and local model:

```bash
uv run -m scripts.stress_scheduler_fixture_repo --in-place
```

If a patch fails to apply, the tool falls back to a whole-file write using the already-generated code and saves the failed diff under `.runtime/failed_patches/` for manual inspection. If both the patch and the whole-file write fail, the run is aborted with a verification failure.

Observability
-------------

`run_monorepo_task` prints a human-readable execution trace to the console at the end of every run, showing each node, its duration, and the first line of any failure reason:

```bash
uv run -m scripts.run_monorepo_task --task "add docstrings to all public methods in foo.py"
```

A full per-run JSONL event log is written to `.runtime/runs/<run_id>.jsonl` for streaming inspection, and an aggregated JSON summary to `.runtime/runs/<run_id>.json`. Inspect the most recent run (requires `jq`):

```bash
ls -1 .runtime/runs/*.jsonl | tail -n1 | xargs cat | jq
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