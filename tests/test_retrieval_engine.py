import os
import tempfile
import unittest

from src.repository.simple_repository_indexer import SimpleRepositoryIndexer
from src.repository.retrieval_engine import SimpleRetrievalEngine
from tests.support.fixture_repo import temporary_fixture_repo


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

    def test_task_terms_influence_ranking_when_no_target(self):
        with tempfile.TemporaryDirectory() as td:
            auth_service = os.path.join(td, "auth_service.py")
            user_profile = os.path.join(td, "user_profile.py")
            misc = os.path.join(td, "misc.py")

            with open(auth_service, "w", encoding="utf-8") as f:
                f.write("def login_user():\n    return True\n")
            with open(user_profile, "w", encoding="utf-8") as f:
                f.write("def profile_name():\n    return 'x'\n")
            with open(misc, "w", encoding="utf-8") as f:
                f.write("def helper():\n    return 0\n")

            snapshot = SimpleRepositoryIndexer().build_snapshot(td)
            selected = SimpleRetrievalEngine().select_files(
                "refactor auth profile flow",
                snapshot,
                target_file=None,
                max_files=3,
            )

            # Files with task-term overlap should rank ahead of unrelated files.
            self.assertIn(os.path.normpath(auth_service), selected[:2])
            self.assertIn(os.path.normpath(user_profile), selected[:2])

    def test_direct_imported_file_ranks_before_reverse_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            target = os.path.join(td, "a.py")
            imported = os.path.join(td, "b.py")
            reverse_dep = os.path.join(td, "z.py")

            with open(target, "w", encoding="utf-8") as f:
                f.write("import b\n")
            with open(imported, "w", encoding="utf-8") as f:
                f.write("def bfunc():\n    return 1\n")
            with open(reverse_dep, "w", encoding="utf-8") as f:
                f.write("import a\n")

            snapshot = SimpleRepositoryIndexer().build_snapshot(td)
            selected = SimpleRetrievalEngine().select_files(
                "refactor a",
                snapshot,
                target_file=os.path.normpath(target),
                max_files=5,
            )

            self.assertEqual(selected[0], os.path.normpath(target))
            self.assertLess(
                selected.index(os.path.normpath(imported)),
                selected.index(os.path.normpath(reverse_dep)),
            )

    def test_sample_repo_v2_ranks_task_chain_files(self):
        with temporary_fixture_repo("sample_repo_v2") as repo_path:
            target = os.path.normpath(os.path.join(repo_path, "app", "main.py"))

            snapshot = SimpleRepositoryIndexer().build_snapshot(str(repo_path))
            selected = SimpleRetrievalEngine().select_files(
                "refactor the task report pipeline and validation helpers",
                snapshot,
                target_file=target,
                max_files=12,
            )

            self.assertEqual(selected[0], target)
            self.assertEqual(selected[1], os.path.normpath(os.path.join(repo_path, "app", "processing", "task_runner.py")))
            self.assertIn(os.path.normpath(os.path.join(repo_path, "scripts", "smoke.py")), selected)
            self.assertIn(os.path.normpath(os.path.join(repo_path, "app", "services", "task_service.py")), selected)
            self.assertIn(os.path.normpath(os.path.join(repo_path, "app", "utils", "validators.py")), selected)
            self.assertIn(os.path.normpath(os.path.join(repo_path, "app", "services", "report_service.py")), selected)
            self.assertLess(
                selected.index(os.path.normpath(os.path.join(repo_path, "app", "processing", "task_runner.py"))),
                selected.index(os.path.normpath(os.path.join(repo_path, "app", "services", "task_service.py"))),
            )


if __name__ == "__main__":
    unittest.main()
