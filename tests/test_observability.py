import json
import unittest
from src.core.runtime_paths import RUNS_DIR, ensure_runtime_dirs

from src.observability.context import RunContext
from src.observability.event_logging_utils import emit_success, emit_failure
from src.observability.logger import write_run_summary


class TestObservabilitySchema(unittest.TestCase):
    def test_jsonl_event_schema(self):
        """Emit a few events and validate that JSONL lines use the compact schema.

        Per-event lines must NOT contain run_id or task (those belong in the
        top-level run summary). Required keys per event: node, status,
        duration_ms, timestamp, payload.
        """
        rc = RunContext.new()

        emit_success(rc, "node_a", {"info": "ok"})
        emit_failure(rc, "node_b", "some error")
        emit_success(rc, "node_c", {"value": 123})

        ensure_runtime_dirs()
        log_path = RUNS_DIR / f"{rc.run_id}.jsonl"
        self.assertTrue(log_path.exists(), "JSONL log file was not created")

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 3)

        for line in lines:
            obj = json.loads(line)
            # Compact schema: no run_id or task per line
            self.assertEqual(set(obj.keys()), {"node", "status", "duration_ms", "timestamp", "payload"})
            self.assertIn(obj["status"], ("success", "failure"))
            self.assertNotIn("run_id", obj)
            self.assertNotIn("task", obj)

    def test_events_accumulated_on_run_context(self):
        """Events emitted during a run must be accumulated on the RunContext."""
        rc = RunContext.new()

        emit_success(rc, "node_a", {"x": 1})
        emit_failure(rc, "node_b", "boom")

        self.assertEqual(len(rc.events), 2)
        self.assertEqual(rc.events[0]["node"], "node_a")
        self.assertEqual(rc.events[0]["status"], "success")
        self.assertEqual(rc.events[1]["node"], "node_b")
        self.assertEqual(rc.events[1]["status"], "failure")
        self.assertEqual(rc.events[1]["payload"], {"error": "boom"})

    def test_run_summary_written(self):
        """write_run_summary must produce a .json file with the correct top-level structure."""
        rc = RunContext.new()
        rc.task = "test task"

        emit_success(rc, "node_a", {"x": 1})
        emit_failure(rc, "node_b", "something failed")

        write_run_summary(rc, "failure")

        ensure_runtime_dirs()
        summary_path = RUNS_DIR / f"{rc.run_id}.json"
        self.assertTrue(summary_path.exists(), ".json summary file was not created")

        summary = json.loads(summary_path.read_text(encoding="utf-8"))

        # Top-level fields
        self.assertEqual(summary["run_id"], rc.run_id)
        self.assertEqual(summary["task"], "test task")
        self.assertEqual(summary["status"], "failure")
        self.assertIn("started_at", summary)

        # Events array
        self.assertEqual(len(summary["events"]), 2)
        for ev in summary["events"]:
            self.assertNotIn("run_id", ev)
            self.assertNotIn("task", ev)
            self.assertIn("node", ev)
            self.assertIn("status", ev)
            self.assertIn("duration_ms", ev)
            self.assertIn("timestamp", ev)
            self.assertIn("payload", ev)
