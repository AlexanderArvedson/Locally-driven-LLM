"""Minimal JSONL logger and run summary writer for per-run observability events.

Provides:
  - `log_event(run_id, event)` — appends a compact event dict as one JSON line
    to `.runtime/runs/<run_id>.jsonl` for streaming/crash durability.
  - `write_run_summary(run_context, final_status)` — writes the fully aggregated
    run object to `.runtime/runs/<run_id>.json` at the end of execution.
  - `format_run_console(run_context, final_status)` — returns a human-readable
    execution trace string suitable for printing to the console.

All file I/O is synchronous and minimal: no buffering, no external dependencies.
"""

import json

from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs


def log_event(run_id: str, event: dict) -> None:
    """Append `event` as one JSON line to the per-run JSONL file.

    Writes compact events (no run_id/task per line) to the canonical
    `.runtime/runs/` directory for streaming and crash durability.
    """
    ensure_runtime_dirs()

    path = RUNS_DIR / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def write_run_summary(run_context, final_status: str) -> None:
    """Write the aggregated run object to `.runtime/runs/<run_id>.json`.

    Produces a single JSON file with run_id, task, and started_at at the top
    level and all node events collected in an `events` array. Called once at
    the end of execution (in a finally block so it fires even on failure).
    """
    ensure_runtime_dirs()

    summary = {
        "run_id": run_context.run_id,
        "task": run_context.task,
        "started_at": run_context.started_at,
        "status": final_status,
        "events": run_context.events,
    }

    path = RUNS_DIR / f"{run_context.run_id}.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def format_run_console(run_context, final_status: str) -> str:
    """Return a human-readable execution trace string for console output.

    Produces a compact summary with one line per node event, a failure hint
    showing the first line of any error payload, and the final run status.
    """
    lines = [
        f"Run:  {run_context.run_id}",
        f"Task: {run_context.task}",
        "",
    ]

    for ev in run_context.events:
        icon = "v" if ev["status"] == "success" else "x"
        lines.append(f"  {icon} {ev['node']} ({ev['duration_ms']}ms)")
        if ev["status"] == "failure":
            error = ev.get("payload", {}).get("error", "")
            if error:
                first_line = error.split("\n")[0]
                lines.append(f"    |_ {first_line}")

    lines.append("")
    lines.append(f"Status: {final_status}")

    return "\n".join(lines)
