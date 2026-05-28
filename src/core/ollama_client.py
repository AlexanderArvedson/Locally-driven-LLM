"""Thin async client wrapper for Ollama HTTP API.

This module provides a minimal `OllamaClient` used by node implementations
to call the Ollama chat endpoint. It keeps the surface intentionally small
for testability. The `LLMResult` dataclass represents a small subset of
response metadata needed by the rest of the codebase.
"""

from typing import List, Dict
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
            timeout: Request timeout in seconds for API calls.
        """
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
    ) -> LLMResult:
        """Send a chat request to the Ollama API and return a parsed result.

        The method expects the Ollama `/api/chat` response to include a
        `message.content` field and may raise `RuntimeError` on HTTP errors.
        """

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        response = await self._client.post(
            f"{self.base_url}/api/chat",
            json=payload,
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