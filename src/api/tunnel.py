from __future__ import annotations

import asyncio

import httpx


async def get_tunnel_url(ngrok_host: str = "ngrok", retries: int = 5, delay: float = 3.0) -> str | None:
    """Retry-poll the ngrok agent API and return the first active HTTPS public URL."""
    for _ in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://{ngrok_host}:4040/api/tunnels", timeout=5.0)
                for tunnel in resp.json().get("tunnels", []):
                    url = tunnel.get("public_url", "")
                    if url.startswith("https://"):
                        return url
        except Exception:
            pass
        await asyncio.sleep(delay)
    return None
