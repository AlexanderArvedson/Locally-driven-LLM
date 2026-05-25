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