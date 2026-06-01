import unittest

from src.retrieval.contracts.retrieval_contract import RetrievalRequest, RetrievalResult


class TestRetrievalRequest(unittest.TestCase):
    """Unit tests for the RetrievalRequest input contract."""

    def test_required_fields_are_stored(self):
        req = RetrievalRequest(task="add docstrings", target_path="utils.py", max_files=5)
        self.assertEqual(req.task, "add docstrings")
        self.assertEqual(req.target_path, "utils.py")
        self.assertEqual(req.max_files, 5)

    def test_target_path_can_be_none(self):
        req = RetrievalRequest(task="refactor", target_path=None, max_files=10)
        self.assertIsNone(req.target_path)


class TestRetrievalResult(unittest.TestCase):
    """Unit tests for the RetrievalResult output contract."""

    def test_defaults_produce_empty_result(self):
        result = RetrievalResult()
        self.assertEqual(result.primary_files, [])
        self.assertEqual(result.supporting_files, [])
        self.assertEqual(result.confidence, 0.0)

    def test_explicit_fields_are_stored(self):
        result = RetrievalResult(
            primary_files=["app/main.py"],
            supporting_files=["app/utils.py", "app/config.py"],
            confidence=0.85,
        )
        self.assertEqual(result.primary_files, ["app/main.py"])
        self.assertEqual(result.supporting_files, ["app/utils.py", "app/config.py"])
        self.assertAlmostEqual(result.confidence, 0.85)

    def test_primary_and_supporting_lists_are_independent(self):
        # Mutable default_factory must give each instance its own list.
        a = RetrievalResult()
        b = RetrievalResult()
        a.primary_files.append("x.py")
        self.assertEqual(b.primary_files, [])

    def test_confidence_boundary_values(self):
        low = RetrievalResult(confidence=0.0)
        high = RetrievalResult(confidence=1.0)
        self.assertEqual(low.confidence, 0.0)
        self.assertEqual(high.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
