from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.processing.task_runner import load_seed_payloads, run_task_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the sample task pipeline.")
    parser.add_argument("--input", help="Path to a JSON file containing task payloads.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of tasks to report.")
    return parser


def _load_payloads(input_path: str) -> list[dict[str, object]]:
    data = Path(input_path).read_text(encoding="utf-8")
    payloads = json.loads(data)
    if not isinstance(payloads, list):
        raise ValueError("input JSON must be a list of task payloads")
    return payloads


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    payloads = _load_payloads(args.input) if args.input else load_seed_payloads()
    output = run_task_pipeline(payloads, limit=args.limit)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())