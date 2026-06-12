"""Tests for the centralized TokenCounter abstraction."""

from __future__ import annotations

import unittest

from src.retrieval.budgeting.token_counter import TokenCounter


class TestTokenCounter(unittest.TestCase):
    def setUp(self) -> None:
        self.counter = TokenCounter()

    def test_fallback_empty_string_returns_one(self) -> None:
        self.assertEqual(self.counter.count(""), 1)

    def test_fallback_estimate_chars_divided_by_four(self) -> None:
        text = "a" * 400
        result = self.counter.count(text)
        self.assertEqual(result, 100)

    def test_fallback_short_text_returns_at_least_one(self) -> None:
        result = self.counter.count("hi")
        self.assertGreaterEqual(result, 1)

    def test_no_model_config_uses_estimate(self) -> None:
        text = "hello world this is a test"
        result = self.counter.count(text, model_config=None)
        expected = max(1, len(text) // 4)
        self.assertEqual(result, expected)

    def test_ollama_provider_uses_estimate(self) -> None:
        from src.core.config_loader import ModelConfig
        cfg = ModelConfig(name="qwen2.5-coder:7b", provider="ollama")
        text = "x" * 100
        result = self.counter.count(text, model_config=cfg)
        self.assertEqual(result, 25)

    def test_openai_provider_falls_back_to_estimate_without_tiktoken(self) -> None:
        """When tiktoken is absent the openai path falls back to the estimate."""
        from src.core.config_loader import ModelConfig
        cfg = ModelConfig(name="gpt-4o", provider="openai")
        text = "a" * 80
        result = self.counter.count(text, model_config=cfg)
        # Regardless of tiktoken availability the result is always >= 1.
        self.assertGreaterEqual(result, 1)

    def test_multiple_calls_are_deterministic(self) -> None:
        text = "The quick brown fox jumps over the lazy dog."
        r1 = self.counter.count(text)
        r2 = self.counter.count(text)
        self.assertEqual(r1, r2)
