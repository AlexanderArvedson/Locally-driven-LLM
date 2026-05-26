"""Check that at least one runtime JSONL run file exists under `.runtime/runs/`.

This script is intentionally tiny and deterministic: CI should run it after the
unit tests to ensure that mocked graph executions emitted run artifacts.
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
    run_files = sorted(RUNS_DIR.glob("*.jsonl"))
    if not run_files:
        print("No runtime run files found in .runtime/runs/; expected at least one")
        return 1
    print(f"Found {len(run_files)} run file(s) in .runtime/runs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
