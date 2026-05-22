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
        model: str = "llama3.1",
        temperature: float = 0.7,
    ) -> LLMResult:

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        resp = await self._client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )

        resp.raise_for_status()
        data = resp.json()

        return LLMResult(
            message=data["message"]["content"],
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )

    async def close(self):
        await self._client.aclose()