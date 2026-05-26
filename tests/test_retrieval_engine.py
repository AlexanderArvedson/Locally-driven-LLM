import os
import tempfile
import unittest

from src.repository.simple_repository_indexer import SimpleRepositoryIndexer
from src.repository.retrieval_engine import SimpleRetrievalEngine


class TestRetrievalEngine(unittest.TestCase):
    def test_select_files_ordering(self):
        with tempfile.TemporaryDirectory() as td:
            # create files a.py imports b and c
            a_path = os.path.join(td, "a.py")
            b_path = os.path.join(td, "b.py")
            c_path = os.path.join(td, "c.py")
            with open(a_path, "w", encoding="utf-8") as f:
                f.write("import b\nimport c\n\ndef foo():\n    return 1\n")
            with open(b_path, "w", encoding="utf-8") as f:
                f.write("def bfunc():\n    pass\n")
            with open(c_path, "w", encoding="utf-8") as f:
                f.write("def cfunc():\n    pass\n")

            indexer = SimpleRepositoryIndexer()
            snapshot = indexer.build_snapshot(td)

            retriever = SimpleRetrievalEngine()
            selected = retriever.select_files("Some task", snapshot, target_file=os.path.normpath(a_path), max_files=10)

            # target should be first
            self.assertGreaterEqual(len(selected), 1)
            self.assertEqual(selected[0], os.path.normpath(a_path))

            # imported files b and c should appear
            self.assertIn(os.path.normpath(b_path), selected)
            self.assertIn(os.path.normpath(c_path), selected)


if __name__ == "__main__":
    unittest.main()
