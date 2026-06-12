from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from src.core import config_loader as app_config


def _minimal_repo(overrides: dict | None = None) -> dict:
    """Return a minimal valid repository entry for test configs."""
    base = {
        "name": "repo",
        "url": "https://example.test/repo.git",
        "base_branch": "main",
        "prefix": "DEV-",
        "local_path": "/tmp/repo",
        "created_at": None,
        "updated_at": None,
        "max_workflow_revision_cycles": 3,
        "credentials": None,
        "models": {
            "LLM": {
                "name": "example-model",
                "provider": "ollama",
                "url": "http://example.test:11434",
            }
        },
    }
    if overrides:
        base.update(overrides)
    return base


def _write_config(tmp_dir: str, repo_overrides: dict | None = None) -> Path:
    config_path = Path(tmp_dir) / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "cron": "0 0 * * *",
                "repositories": [_minimal_repo(repo_overrides)],
            }
        ),
        encoding="utf-8",
    )
    return config_path


class TestConfig(unittest.TestCase):
    def test_example_config_loads_without_error(self) -> None:
        """config.example.json must be loadable so CI and fresh checkouts work."""
        loaded = app_config.load_config(app_config.EXAMPLE_CONFIG_PATH)
        self.assertGreater(len(loaded.repositories), 0)
        self.assertEqual(loaded.repositories[0].max_workflow_revision_cycles, 3)
        self.assertIn("coder", loaded.repositories[0].models)

    def test_load_config_supports_explicit_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = _write_config(tmp_dir)
            loaded = app_config.load_config(config_path)

        self.assertEqual(loaded.repositories[0].max_workflow_revision_cycles, 3)
        self.assertEqual(loaded.repositories[0].models["LLM"].name, "example-model")
        self.assertEqual(loaded.repositories[0].models["LLM"].url, "http://example.test:11434")

    def test_load_config_missing_file_raises(self) -> None:
        missing = Path(tempfile.gettempdir()) / "missing-config.json"
        if missing.exists():
            missing.unlink()

        with self.assertRaises(FileNotFoundError):
            app_config.load_config(missing)

    # --- max_workflow_revision_cycles validation ---

    def test_max_workflow_revision_cycles_minimum_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = _write_config(tmp_dir, {"max_workflow_revision_cycles": 0})
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    def test_max_workflow_revision_cycles_must_be_int(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = _write_config(tmp_dir, {"max_workflow_revision_cycles": "three"})
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    # --- ModelConfig inference fields ---

    def test_model_temperature_null_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["temperature"] = None
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            loaded = app_config.load_config(config_path)
            self.assertIsNone(loaded.repositories[0].models["LLM"].temperature)

    def test_model_temperature_non_null_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["temperature"] = 0.5
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            loaded = app_config.load_config(config_path)
            self.assertAlmostEqual(loaded.repositories[0].models["LLM"].temperature, 0.5)

    def test_model_temperature_negative_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["temperature"] = -0.1
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    def test_model_max_tokens_null_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["max_tokens"] = None
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            loaded = app_config.load_config(config_path)
            self.assertIsNone(loaded.repositories[0].models["LLM"].max_tokens)

    def test_model_max_tokens_positive_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["max_tokens"] = 2048
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            loaded = app_config.load_config(config_path)
            self.assertEqual(loaded.repositories[0].models["LLM"].max_tokens, 2048)

    def test_model_max_tokens_zero_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["max_tokens"] = 0
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    def test_model_timeout_seconds_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = _write_config(tmp_dir)
            loaded = app_config.load_config(config_path)
            self.assertEqual(loaded.repositories[0].models["LLM"].timeout_seconds, 300)

    def test_model_timeout_seconds_zero_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["models"]["LLM"]["timeout_seconds"] = 0
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    # --- RetrievalConfig ---

    def test_retrieval_config_defaults_when_block_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = _write_config(tmp_dir)
            loaded = app_config.load_config(config_path)
            rc = loaded.repositories[0].retrieval
            self.assertEqual(rc.max_context_files, 20)
            self.assertEqual(rc.max_context_tokens, 12000)
            self.assertEqual(rc.limit_reached_behavior, "warn")

    def test_retrieval_config_explicit_values_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["retrieval"] = {
                "max_context_files": 5,
                "max_context_tokens": 4000,
                "limit_reached_behavior": "fail",
            }
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            loaded = app_config.load_config(config_path)
            rc = loaded.repositories[0].retrieval
            self.assertEqual(rc.max_context_files, 5)
            self.assertEqual(rc.max_context_tokens, 4000)
            self.assertEqual(rc.limit_reached_behavior, "fail")

    def test_retrieval_max_context_files_zero_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["retrieval"] = {"max_context_files": 0}
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    def test_retrieval_max_context_tokens_zero_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["retrieval"] = {"max_context_tokens": 0}
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    def test_retrieval_invalid_limit_reached_behavior_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = _minimal_repo()
            repo["retrieval"] = {"limit_reached_behavior": "invalid"}
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                app_config.load_config(config_path)

    def test_retrieval_all_valid_behaviors_accepted(self) -> None:
        for behavior in ("ignore", "warn", "fail"):
            with tempfile.TemporaryDirectory() as tmp_dir:
                repo = _minimal_repo()
                repo["retrieval"] = {"limit_reached_behavior": behavior}
                config_path = Path(tmp_dir) / "config.json"
                config_path.write_text(json.dumps({"cron": "0 0 * * *", "repositories": [repo]}), encoding="utf-8")
                loaded = app_config.load_config(config_path)
                self.assertEqual(loaded.repositories[0].retrieval.limit_reached_behavior, behavior)
