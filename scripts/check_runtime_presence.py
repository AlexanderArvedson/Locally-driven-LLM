"""Check that at least one runtime JSONL run file exists under `.runtime/runs/`.

This script is intentionally tiny and deterministic: CI should run it after the
unit tests to ensure that mocked graph executions emitted run artifacts.

Also reports on `.json` summary files produced by `write_run_summary` at run
completion. Their absence is informational only (they are not written by unit
tests that skip the executor's finalize path).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs  # noqa: E402


def main() -> int:
    ensure_runtime_dirs()
    jsonl_files = sorted(RUNS_DIR.glob("*.jsonl"))
    json_files = sorted(RUNS_DIR.glob("*.json"))

    if not jsonl_files:
        print("No runtime run files found in .runtime/runs/; expected at least one")
        return 1

    print(
        f"Found {len(jsonl_files)} JSONL event file(s) and "
        f"{len(json_files)} run summary file(s) in .runtime/runs/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
