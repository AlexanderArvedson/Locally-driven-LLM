"""Thin async client wrapper for Ollama HTTP API.

This module provides a minimal `OllamaClient` used by node implementations
to call the Ollama chat endpoint. It keeps the surface intentionally small
for testability. The `LLMResult` dataclass represents a small subset of
response metadata needed by the rest of the codebase.

Inference parameters (temperature, max_tokens, timeout_seconds, num_gpu) are
accepted per-request so each model role can apply its own configured values.
GPU offloading is controlled via ``num_gpu``: pass ``-1`` (auto / all layers)
to use the GPU, or ``0`` to force CPU-only inference.
"""

from typing import List, Dict, Optional
import httpx
from dataclasses import dataclass


def _gpu_layers(allow_gpu: bool) -> int:
    """Return the Ollama ``num_gpu`` value for a given ``allow_gpu`` flag.

    Ollama interprets ``-1`` as "offload all layers automatically" and ``0``
    as CPU-only. There is no runtime GPU-presence check here — Ollama itself
    gracefully falls back to CPU when no compatible GPU is found, so passing
    ``-1`` on a CPU-only host is safe.
    """
    return -1 if allow_gpu else 0


@dataclass
class LLMResult:
    message: str
    input_tokens: int
    output_tokens: int


@dataclass
class EmbedResult:
    embedding: list[float]


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
        allow_gpu: bool = True,
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
            allow_gpu: When ``True``, Ollama offloads all layers to the GPU
                (``num_gpu=-1``). When ``False``, inference runs on CPU only
                (``num_gpu=0``).

        Raises:
            RuntimeError: On HTTP error responses from Ollama.
        """
        options: dict = {"num_gpu": _gpu_layers(allow_gpu)}
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

    async def embed(
        self,
        text: str,
        model: str,
        timeout_seconds: int = 120,
        allow_gpu: bool = True,
    ) -> EmbedResult:
        """Send an embedding request to the Ollama API and return the vector.

        Args:
            text: The text to embed.
            model: Ollama embedding model identifier (e.g. ``"nomic-embed-text"``).
            timeout_seconds: Per-request wall-clock timeout.
            allow_gpu: When ``True``, offloads to GPU (``num_gpu=-1``).

        Raises:
            RuntimeError: On HTTP error responses from Ollama.
        """
        payload: dict = {
            "model": model,
            "prompt": text,
            "options": {"num_gpu": _gpu_layers(allow_gpu)},
        }

        response = await self._client.post(
            f"{self.base_url}/api/embeddings",
            json=payload,
            timeout=timeout_seconds,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama embed request failed: {e}") from e

        return EmbedResult(embedding=response.json()["embedding"])

    async def close(self):
        """Close the underlying HTTP client connection pool."""
        await self._client.aclose()
