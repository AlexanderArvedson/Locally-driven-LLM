import os
import tempfile
import unittest

from src.retrieval.indexing.ast_indexer import AstIndexer
from src.retrieval.ranking.heuristic_ranker import HeuristicRanker
from src.retrieval.assembly.context_assembler import ContextAssembler


class TestContextBuilder(unittest.TestCase):
    def test_context_caps_and_contents(self):
        with tempfile.TemporaryDirectory() as td:
            # create multiple files with symbols
            paths = []
            for i in range(5):
                p = os.path.join(td, f"m{i}.py")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(f"def func_{i}():\n    pass\n")
                paths.append(p)

            # create target that imports first two
            target = os.path.join(td, "target.py")
            with open(target, "w", encoding="utf-8") as f:
                f.write("import m0\nimport m1\n\ndef main():\n    pass\n")

            indexer = AstIndexer()
            snapshot = indexer.build_snapshot(td)
            ranker = HeuristicRanker()
            selected = ranker.rank_candidates("Task", snapshot, target_file=os.path.normpath(target), max_files=10)

            assembler = ContextAssembler()
            ctx = assembler.build("Task", os.path.normpath(target), selected, snapshot, max_files=4, max_symbols_per_file=1, max_total_context_chars=100)

            self.assertEqual(ctx.primary_file, os.path.normpath(target))
            # max_files=4 should limit related_files
            self.assertLessEqual(len(ctx.related_files), 4)
            # each file's symbols capped to 1
            for syms in ctx.related_symbols.values():
                self.assertLessEqual(len(syms), 1)


if __name__ == "__main__":
    unittest.main()
