# Logger for graph execution events. Provides a simple function to log events to a JSONL file,

import json
from pathlib import Path


LOG_DIR = Path("logs/runs")

# Logs an event for a given run ID. The event is a dictionary that will be serialized to JSON 
# and appended to a log file named after the run ID.
def log_event(run_id: str, event: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    path = LOG_DIR / f"{run_id}.jsonl"

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
