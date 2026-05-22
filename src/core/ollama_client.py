from typing import List, Dict
import httpx
from dataclasses import dataclass


@dataclass
class LLMResult:
    message: str
    input_tokens: int
    output_tokens: int

class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 300.0):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
    ) -> LLMResult:

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
        await self._client.aclose()