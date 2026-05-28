from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from src import config_loader as app_config


class TestConfig(unittest.TestCase):
    def test_module_constants_match_config_file(self) -> None:
        raw = json.loads(app_config.CONFIG_PATH.read_text(encoding="utf-8"))
        repository = raw["repositories"][0]

        self.assertEqual(app_config.APP_CONFIG.cron, raw["cron"])
        self.assertEqual(app_config.APP_CONFIG.repositories[0].max_iterations, repository["max_iterations"])
        self.assertEqual(app_config.get_repository_config().name, repository["name"])
        self.assertEqual(app_config.OLLAMA_BASE_URL, repository["models"]["LLM"]["url"])
        self.assertEqual(app_config.CODER_MODEL, repository["models"]["LLM"]["name"])
        self.assertEqual(app_config.MAX_ITERATIONS, repository["max_iterations"])

    def test_load_config_supports_explicit_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "cron": "0 0 * * *",
                        "repositories": [
                            {
                                "name": "repo",
                                "url": "https://example.test/repo.git",
                                "base_branch": "main",
                                "prefix": "DEV-",
                                "local_path": "/tmp/repo",
                                "created_at": None,
                                "updated_at": None,
                                "context_path": "/tmp/context",
                                "max_iterations": 4,
                                "credentials": None,
                                "models": {
                                    "LLM": {
                                        "name": "example-model",
                                        "provider": "ollama",
                                        "url": "http://example.test:11434",
                                    }
                                },
                                "slack_webhook_url": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = app_config.load_config(config_path)

        self.assertEqual(loaded.repositories[0].max_iterations, 4)
        self.assertEqual(loaded.repositories[0].models["LLM"].name, "example-model")
        self.assertEqual(loaded.repositories[0].models["LLM"].url, "http://example.test:11434")

    def test_load_config_missing_file_raises(self) -> None:
        missing = Path(tempfile.gettempdir()) / "missing-config.json"
        if missing.exists():
            missing.unlink()

        with self.assertRaises(FileNotFoundError):
            app_config.load_config(missing)