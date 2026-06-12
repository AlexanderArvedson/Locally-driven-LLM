import os
import pytest

from src.core.ollama_client import EmbedResult, OllamaClient, LLMResult


@pytest.fixture(autouse=True)
def mock_ollama_in_ci(monkeypatch):
    """When running under CI, replace network calls to Ollama with a fast mock.

    This keeps CI deterministic and avoids depending on external services.
    The fixture is autouse but only activates when the `CI` environment
    variable is set by the runner.
    """
    if os.getenv("CI"):
        async def fake_chat(self, *args, **kwargs):
            return LLMResult(message="[mocked]", input_tokens=0, output_tokens=0)

        async def fake_embed(self, *args, **kwargs):
            return EmbedResult(embedding=[0.1] * 768)

        async def fake_close(self):
            return None

        monkeypatch.setattr(OllamaClient, "chat", fake_chat)
        monkeypatch.setattr(OllamaClient, "embed", fake_embed)
        monkeypatch.setattr(OllamaClient, "close", fake_close)
