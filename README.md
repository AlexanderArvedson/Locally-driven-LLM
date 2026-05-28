# Locally-driven-langgraph-LLM

Quick notes (how to run the file-edit MVP):

Before running the app, create a local `config.json` from `config.example.json` and edit the values for your machine and model setup. The repository ignores `config.json`, so each checkout can keep its own runtime settings. The example file is just a template; the local file is where the real repo-specific values live. The `max_iterations` field under each repository controls the allowed iterations for workflows. `api_key` is optional and is only needed for hosted providers; leave it `null` when using local hosting such as Ollama.

```bash
cp config.example.json config.json
```

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