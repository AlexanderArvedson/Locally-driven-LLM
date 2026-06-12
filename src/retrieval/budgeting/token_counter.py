"""Centralized token counting abstraction.

All retrieval token budgeting must go through ``TokenCounter``. No retrieval
code should contain provider-specific token estimation logic directly.

Provider strategy (tried in order):
  1. OpenAI-compatible providers  → tiktoken (optional dependency)
  2. All other providers          → character-based estimate (len(text) // 4)

The ``tiktoken`` import is guarded so the package is not required at runtime.
When absent the estimator falls through to the character-based fallback
transparently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.config_loader import ModelConfig


_CHARS_PER_TOKEN = 4


def _estimate(text: str) -> int:
    """Character-based token estimate used as a universal fallback."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


class TokenCounter:
    """Estimates token counts for retrieval budgeting.

    Selects the best available counting strategy based on the provider
    declared in ``model_config``. Falls back to a character-based estimate
    when no compatible tokenizer is found.
    """

    def count(self, text: str, model_config: "ModelConfig | None" = None) -> int:
        """Return an estimated token count for ``text``.

        Args:
            text: The text to count tokens in.
            model_config: Optional model configuration. When supplied and the
                provider is ``"openai"``, tiktoken is used if available.

        Returns:
            Estimated token count (always >= 1).
        """
        if not text:
            return 1

        if model_config is not None and model_config.provider == "openai":
            result = self._count_with_tiktoken(text, model_config.name)
            if result is not None:
                return result

        return _estimate(text)

    def _count_with_tiktoken(self, text: str, model_name: str) -> int | None:
        """Try to count tokens with tiktoken; return None if unavailable."""
        try:
            import tiktoken  # type: ignore[import-untyped]
        except ImportError:
            return None

        try:
            enc = tiktoken.encoding_for_model(model_name)
        except KeyError:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                return None
        except Exception:
            return None

        try:
            return len(enc.encode(text))
        except Exception:
            return None
