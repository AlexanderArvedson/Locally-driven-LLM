"""Tests for file_writer_node, focusing on patch fallback recovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.observability.context import RunContext


def _make_state(target_file: str, generated_code: str, generated_diff: str | None = None) -> dict:
    state: dict = {
        "task": "test task",
        "target_file": target_file,
        "generated_code": generated_code,
    }
    if generated_diff is not None:
        state["generated_diff"] = generated_diff
    return state


class TestFileWriterPatchFallback(unittest.IsolatedAsyncioTestCase):
    async def test_whole_file_write_succeeds_when_no_diff(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sample.py"
            target.write_text("x = 1\n", encoding="utf-8")
            state = _make_state(str(target), "x = 2\n")
            run_context = RunContext.new()

            from src.graph.nodes.file_writer import file_writer_node
            result = await file_writer_node(state, run_context)

            self.assertIn("updated_code", result)
            # strip_code_fences strips trailing newlines from generated_code
            self.assertEqual(target.read_text(encoding="utf-8").rstrip(), "x = 2")

    async def test_patch_fallback_writes_generated_code_when_diff_fails(self):
        """When apply_unified raises, the node falls back to writing generated_code."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sample.py"
            target.write_text("x = 1\n", encoding="utf-8")
            state = _make_state(str(target), "x = 99\n", generated_diff="@@ bad diff @@\n")
            run_context = RunContext.new()

            with patch("src.graph.nodes.file_writer.apply_unified", side_effect=ValueError("hunk mismatch")):
                from src.graph.nodes.file_writer import file_writer_node
                result = await file_writer_node(state, run_context)

            # Node should succeed via whole-file fallback
            self.assertIn("updated_code", result)
            self.assertNotIn("verification_passed", result)
            # strip_code_fences strips trailing newlines from generated_code
            self.assertEqual(target.read_text(encoding="utf-8").rstrip(), "x = 99")

    async def test_patch_fallback_fails_if_both_diff_and_write_fail(self):
        """When both apply_unified and write_file raise, node returns verification failure."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sample.py"
            target.write_text("x = 1\n", encoding="utf-8")
            state = _make_state(str(target), "x = 99\n", generated_diff="@@ bad diff @@\n")
            run_context = RunContext.new()

            with (
                patch("src.graph.nodes.file_writer.apply_unified", side_effect=ValueError("hunk mismatch")),
                patch("src.graph.nodes.file_writer.write_file", side_effect=OSError("disk full")),
            ):
                from src.graph.nodes.file_writer import file_writer_node
                result = await file_writer_node(state, run_context)

            self.assertFalse(result.get("verification_passed"))
            self.assertIn("disk full", result.get("verification_feedback", ""))

    async def test_write_failure_without_diff_returns_verification_failure(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sample.py"
            target.write_text("x = 1\n", encoding="utf-8")
            state = _make_state(str(target), "x = 99\n")
            run_context = RunContext.new()

            with patch("src.graph.nodes.file_writer.write_file", side_effect=OSError("disk full")):
                from src.graph.nodes.file_writer import file_writer_node
                result = await file_writer_node(state, run_context)

            self.assertFalse(result.get("verification_passed"))
            self.assertIn("disk full", result.get("verification_feedback", ""))


if __name__ == "__main__":
    unittest.main()
