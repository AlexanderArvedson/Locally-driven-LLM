"""Tests for ContextBudget with token-based limits and retrieval statistics."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.retrieval.budgeting.context_budget import ContextBudget
from src.retrieval.budgeting.token_counter import TokenCounter


def _write_files(tmp_dir: str, contents: dict[str, str]) -> dict[str, str]:
    """Write files to tmp_dir and return a mapping of name → absolute path."""
    paths = {}
    for name, text in contents.items():
        p = Path(tmp_dir) / name
        p.write_text(text, encoding="utf-8")
        paths[name] = str(p)
    return paths


class TestContextBudgetTokenLimits(unittest.TestCase):
    def setUp(self) -> None:
        self.counter = TokenCounter()

    def test_candidate_files_equals_total_ranked_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {"a.py": "x" * 40, "b.py": "y" * 40, "c.py": "z" * 40})
            ranked = [files["a.py"], files["b.py"], files["c.py"]]
            budget = ContextBudget(max_files=10, max_context_tokens=10000)
            alloc = budget.allocate(ranked)
            self.assertEqual(alloc.candidate_files, 3)

    def test_file_count_limit_sets_limit_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {f"f{i}.py": "x" * 10 for i in range(5)})
            ranked = list(files.values())
            budget = ContextBudget(max_files=2, max_context_tokens=10000)
            alloc = budget.allocate(ranked)
            self.assertLessEqual(len(alloc.selected_files), 2)
            self.assertTrue(alloc.limit_hit)

    def test_token_budget_limit_sets_limit_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # 400 chars → estimate 100 tokens each; 3 files = 300 tokens total
            files = _write_files(tmp, {f"f{i}.py": "x" * 400 for i in range(3)})
            ranked = list(files.values())
            # Allow only 150 tokens → only 1 file should fit
            budget = ContextBudget(max_files=10, max_context_tokens=150, token_counter=self.counter)
            alloc = budget.allocate(ranked)
            self.assertLess(len(alloc.selected_files), 3)
            self.assertTrue(alloc.limit_hit)

    def test_target_file_always_included_even_over_token_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {"target.py": "x" * 400, "other.py": "y" * 400})
            target = files["target.py"]
            ranked = [files["target.py"], files["other.py"]]
            # Budget so tight only one file-worth of tokens is allowed
            budget = ContextBudget(max_files=1, max_context_tokens=5, token_counter=self.counter)
            alloc = budget.allocate(ranked, target_file=target)
            self.assertIn(target, alloc.selected_files)

    def test_limit_hit_false_when_no_limit_reached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {"a.py": "hello", "b.py": "world"})
            ranked = list(files.values())
            budget = ContextBudget(max_files=10, max_context_tokens=10000)
            alloc = budget.allocate(ranked)
            self.assertFalse(alloc.limit_hit)
            self.assertEqual(alloc.files_dropped, 0)

    def test_token_budget_used_is_nonzero_for_non_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {"a.py": "x" * 100})
            budget = ContextBudget(max_files=10, max_context_tokens=10000, token_counter=self.counter)
            alloc = budget.allocate(list(files.values()))
            self.assertGreater(alloc.token_budget_used, 0)

    def test_empty_ranked_list_returns_only_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {"target.py": "content"})
            target = files["target.py"]
            budget = ContextBudget(max_files=10, max_context_tokens=10000)
            alloc = budget.allocate([], target_file=target)
            self.assertEqual(alloc.selected_files, [target])
            self.assertFalse(alloc.limit_hit)

    def test_files_dropped_count_is_accurate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = _write_files(tmp, {f"f{i}.py": "x" for i in range(4)})
            ranked = list(files.values())
            budget = ContextBudget(max_files=2, max_context_tokens=10000)
            alloc = budget.allocate(ranked)
            self.assertEqual(alloc.files_dropped, alloc.candidate_files - len(alloc.selected_files))
