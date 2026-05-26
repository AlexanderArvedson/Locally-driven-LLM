"""Validate runtime JSONL observability events in .runtime/runs/.

This script performs a minimal deterministic contract check for emitted run
logs without introducing full JSON Schema tooling. It verifies that each line
is valid JSON, is an object, and contains the required top-level keys.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs  # noqa: E402


REQUIRED_KEYS = {"run_id", "node", "status", "duration_ms", "task", "timestamp"}


def _validate_event(event: object) -> tuple[bool, str]:
    if not isinstance(event, dict):
        return False, "event is not a JSON object"

    missing_keys = sorted(REQUIRED_KEYS - set(event.keys()))
    if missing_keys:
        return False, f"missing required keys: {', '.join(missing_keys)}"

    if not isinstance(event["run_id"], str) or not event["run_id"]:
        return False, "run_id must be a non-empty string"
    if not isinstance(event["node"], str) or not event["node"]:
        return False, "node must be a non-empty string"
    if event["status"] not in {"success", "failure"}:
        return False, 'status must be "success" or "failure"'
    if not isinstance(event["duration_ms"], int) or event["duration_ms"] < 0:
        return False, "duration_ms must be a non-negative integer"
    if not isinstance(event["task"], str):
        return False, "task must be a string"
    if not isinstance(event["timestamp"], str) or not event["timestamp"]:
        return False, "timestamp must be a non-empty string"

    return True, ""


def main() -> int:
    ensure_runtime_dirs()

    run_log_paths = sorted(RUNS_DIR.glob("*.jsonl"))
    total_events = 0

    if not run_log_paths:
        print("Validated 0 events across 0 run logs")
        return 0

    for run_log_path in run_log_paths:
        try:
            lines = run_log_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            print(f"{run_log_path}: failed to read file: {exc}")
            return 1

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                print(f"{run_log_path}: line {line_number}: empty line")
                return 1

            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"{run_log_path}: line {line_number}: malformed JSON: {exc.msg}")
                return 1

            is_valid, message = _validate_event(event)
            if not is_valid:
                print(f"{run_log_path}: line {line_number}: {message}")
                return 1

            total_events += 1

    print(f"Validated {total_events} events across {len(run_log_paths)} run logs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
