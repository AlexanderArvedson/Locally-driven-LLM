"""Thin async client wrapper for Ollama HTTP API.

This module provides a minimal `OllamaClient` used by node implementations
to call the Ollama chat endpoint. It keeps the surface intentionally small
for testability. The `LLMResult` dataclass represents a small subset of
response metadata needed by the rest of the codebase.

Inference parameters (temperature, max_tokens, timeout_seconds) are accepted
per-request so each model role can apply its own configured values.
"""

from typing import List, Dict, Optional
import httpx
from dataclasses import dataclass


@dataclass
class LLMResult:
    message: str
    input_tokens: int
    output_tokens: int


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 600.0):
        """Create a new `OllamaClient`.

        Args:
            base_url: Base URL of the Ollama HTTP server (e.g. http://localhost:11434).
            timeout: Global fallback timeout in seconds. Overridden per-request
                by the ``timeout_seconds`` argument to ``chat()``.
        """
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        timeout_seconds: int = 300,
    ) -> LLMResult:
        """Send a chat request to the Ollama API and return a parsed result.

        Args:
            messages: Conversation history in ``[{"role": ..., "content": ...}]``
                format.
            model: Ollama model identifier (e.g. ``"qwen2.5-coder:7b"``).
            temperature: Sampling temperature. Omitted from the request when
                ``None``, letting the model use its default.
            max_tokens: Maximum tokens to generate (mapped to Ollama's
                ``num_predict``). Omitted from the request when ``None``.
            num_ctx: Context window size (mapped to Ollama's ``num_ctx``).
                Omitted from the request when ``None``.
            timeout_seconds: Per-request wall-clock timeout. Overrides the
                global client timeout for this call.

        Raises:
            RuntimeError: On HTTP error responses from Ollama.
        """
        options: dict = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if num_ctx is not None:
            options["num_ctx"] = num_ctx

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options

        response = await self._client.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=timeout_seconds,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

        data = response.json()

        return LLMResult(
            message=data["message"]["content"],
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )

    async def close(self):
        """Close the underlying HTTP client connection pool."""
        await self._client.aclose()
