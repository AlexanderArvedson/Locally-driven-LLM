import os
import tempfile
import unittest

from src.retrieval.indexing.ast_indexer import AstIndexer


class TestRepositoryIndexer(unittest.TestCase):
    def test_index_basic_files(self):
        with tempfile.TemporaryDirectory() as td:
            a_path = os.path.join(td, "a.py")
            b_path = os.path.join(td, "b.py")
            with open(a_path, "w", encoding="utf-8") as f:
                f.write("import b\n\ndef foo():\n    \"\"\"doc\"\"\"\n    return 1\n")
            with open(b_path, "w", encoding="utf-8") as f:
                f.write("class Bar:\n    def method(self):\n        pass\n")

            indexer = AstIndexer()
            snapshot = indexer.build_snapshot(td)

            # two python files indexed
            self.assertEqual(len(snapshot.files), 2)

            a_norm = os.path.normpath(a_path)
            b_norm = os.path.normpath(b_path)

            paths = [os.path.normpath(f.path) for f in snapshot.files]
            self.assertIn(a_norm, paths)
            self.assertIn(b_norm, paths)

            node_a = snapshot.get_file(a_norm)
            self.assertIsNotNone(node_a)
            self.assertIn("foo", [s.name for s in node_a.symbols])

            node_b = snapshot.get_file(b_norm)
            self.assertIsNotNone(node_b)
            names = [s.name for s in node_b.symbols]
            self.assertIn("Bar", names)
            self.assertIn("Bar.method", names)


if __name__ == "__main__":
    unittest.main()
