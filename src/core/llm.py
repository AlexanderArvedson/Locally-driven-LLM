import httpx

class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 300.0):
        self.base_url = base_url
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(self, model: str, prompt: str):

    
    async def close(self):
        await self._client.aclose()