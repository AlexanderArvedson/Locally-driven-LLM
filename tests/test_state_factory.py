import unittest

from src.scheduler.task_request import TaskRequest
from src.scheduler.state_factory import GraphStateFactory


class TestGraphStateFactory(unittest.TestCase):
    """Unit tests for GraphStateFactory.from_task_request."""

    def _make_request(self, **kwargs) -> TaskRequest:
        defaults = {"task": "refactor foo", "repo_path": "/repo"}
        return TaskRequest(**{**defaults, **kwargs})

    # --- Required fields always present ---

    def test_task_is_set_from_request(self):
        state = GraphStateFactory.from_task_request(self._make_request(task="write tests"))
        self.assertEqual(state["task"], "write tests")

    def test_repo_path_is_set_from_request(self):
        state = GraphStateFactory.from_task_request(self._make_request(repo_path="/my/repo"))
        self.assertEqual(state["repo_path"], "/my/repo")

    def test_task_request_stored_in_state(self):
        req = self._make_request()
        state = GraphStateFactory.from_task_request(req)
        self.assertIs(state["task_request"], req)

    # --- target_path / target_file mapping ---

    def test_target_file_set_when_target_path_provided(self):
        req = self._make_request(target_path="app/main.py")
        state = GraphStateFactory.from_task_request(req)
        self.assertEqual(state["target_file"], "app/main.py")

    def test_target_file_absent_when_target_path_is_none(self):
        req = self._make_request(target_path=None)
        state = GraphStateFactory.from_task_request(req)
        self.assertNotIn("target_file", state)

    def test_target_file_absent_by_default(self):
        # TaskRequest.target_path defaults to None.
        req = TaskRequest(task="refactor", repo_path="/repo")
        state = GraphStateFactory.from_task_request(req)
        self.assertNotIn("target_file", state)

    # --- No extra keys are injected ---

    def test_state_contains_only_expected_keys_without_target(self):
        req = TaskRequest(task="refactor", repo_path="/repo")
        state = GraphStateFactory.from_task_request(req)
        self.assertEqual(set(state.keys()), {"task", "repo_path", "task_request"})

    def test_state_contains_only_expected_keys_with_target(self):
        req = TaskRequest(task="refactor", repo_path="/repo", target_path="a.py")
        state = GraphStateFactory.from_task_request(req)
        self.assertEqual(set(state.keys()), {"task", "repo_path", "task_request", "target_file"})

    # --- TaskRequest is the single source of truth ---

    def test_task_request_fields_match_state_fields(self):
        req = TaskRequest(task="fix bug", repo_path="/src", target_path="lib/core.py")
        state = GraphStateFactory.from_task_request(req)
        self.assertEqual(state["task"], req.task)
        self.assertEqual(state["repo_path"], req.repo_path)
        self.assertEqual(state["target_file"], req.target_path)


class TestTaskRequestDefaults(unittest.TestCase):
    """Unit tests for TaskRequest field defaults."""

    def test_target_path_defaults_to_none(self):
        req = TaskRequest(task="t", repo_path="/r")
        self.assertIsNone(req.target_path)

    def test_allow_multi_file_defaults_to_true(self):
        req = TaskRequest(task="t", repo_path="/r")
        self.assertTrue(req.allow_multi_file)

    def test_max_files_defaults_to_ten(self):
        req = TaskRequest(task="t", repo_path="/r")
        self.assertEqual(req.max_files, 10)


if __name__ == "__main__":
    unittest.main()
