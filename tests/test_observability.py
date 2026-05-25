import json
import unittest
from pathlib import Path
from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs

from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_success, emit_failure


class TestObservabilitySchema(unittest.TestCase):
    def test_jsonl_event_schema(self):
        """Schema-based test: emit a few events and validate JSONL format.

        This test writes events for three logical nodes and asserts each line is
        valid JSON with the required top-level keys and a consistent run_id.
        """
        rc = RunContext.new()

        # Emit three events
        emit_success(rc, "node_a", "task-a", {"info": "ok"})
        emit_failure(rc, "node_b", "task-a", "some error")
        emit_success(rc, "node_c", "task-a", {"value": 123})

        ensure_runtime_dirs()
        log_path = RUNS_DIR / f"{rc.run_id}.jsonl"
        self.assertTrue(log_path.exists(), "JSONL log file was not created")

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 3)

        for line in lines:
            obj = json.loads(line)
            # required top-level keys
            self.assertEqual(set(obj.keys()), {"run_id", "node", "status", "duration_ms", "task", "timestamp", "payload"})
            self.assertEqual(obj["run_id"], rc.run_id)
            self.assertIn(obj["status"], ("success", "failure"))
