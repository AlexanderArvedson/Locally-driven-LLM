import unittest
import tempfile
from pathlib import Path

from src.tools.patches import generate_ndiff, apply_ndiff, generate_unified, apply_unified
from src.tools.files import atomic_write_bytes


class TestNdiffPatches(unittest.TestCase):
    def test_patch_applies_and_produces_valid_python(self):
        original = "def add(a, b):\n    return a + b\n"
        modified = (
            "from typing import Union\n\n"
            "def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:\n"
            "    return a + b\n"
        )

        nd = generate_ndiff(original, modified)

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tmp.py"
            path.write_text(original, encoding="utf-8")

            apply_ndiff(str(path), nd)

            result = path.read_text(encoding="utf-8")

            self.assertEqual(result.rstrip(), modified.rstrip())
            compile(result, "<generated>", "exec")
            self.assertIn("Union[int, float]", result)


class TestUnifiedPatches(unittest.TestCase):
    def test_apply_unified_roundtrip(self):
        original = "x = 1\ny = 2\nz = 3\n"
        modified = "x = 1\ny = 99\nz = 3\n"

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tmp.py"
            path.write_text(original, encoding="utf-8")

            diff = generate_unified(original, modified)
            apply_unified(str(path), diff)

            self.assertEqual(path.read_text(encoding="utf-8"), modified)

    def test_apply_unified_preserves_crlf(self):
        original = "a = 1\r\nb = 2\r\n"
        modified = "a = 1\r\nb = 99\r\n"

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tmp.py"
            path.write_bytes(original.encode("utf-8"))

            diff = generate_unified(original, modified)
            apply_unified(str(path), diff)

            result = path.read_bytes().decode("utf-8")
            self.assertIn("\r\n", result)
            self.assertEqual(result, modified)

    def test_apply_unified_empty_diff_is_noop(self):
        original = "x = 1\n"

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tmp.py"
            path.write_text(original, encoding="utf-8")

            apply_unified(str(path), "")

            self.assertEqual(path.read_text(encoding="utf-8"), original)


class TestAtomicWrite(unittest.TestCase):
    def test_atomic_write_produces_correct_content(self):
        data = b"hello atomic world\n"

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.txt"
            atomic_write_bytes(path, data)

            self.assertEqual(path.read_bytes(), data)

    def test_atomic_write_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.txt"
            path.write_bytes(b"old content")

            atomic_write_bytes(path, b"new content")

            self.assertEqual(path.read_bytes(), b"new content")

    def test_atomic_write_leaves_no_temp_file_on_success(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.txt"
            atomic_write_bytes(path, b"data")

            # Only the target file should exist, no leftover temp file
            files = list(Path(td).iterdir())
            self.assertEqual(files, [path])


if __name__ == "__main__":
    unittest.main()
