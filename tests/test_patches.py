import unittest
import tempfile
from pathlib import Path

from src.tools.patches import generate_ndiff, apply_ndiff


class TestPatches(unittest.TestCase):
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

            # apply the generated ndiff
            apply_ndiff(str(path), nd)

            result = path.read_text(encoding="utf-8")

            # patch applied (ignore trailing newlines)
            self.assertEqual(result.rstrip(), modified.rstrip())

            # output is valid python
            compile(result, "<generated>", "exec")

            # expected change present
            self.assertIn("Union[int, float]", result)


if __name__ == "__main__":
    unittest.main()
