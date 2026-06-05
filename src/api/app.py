"""FastAPI application.

Provides a health check endpoint. Slack slash commands are handled via
Socket Mode (see src/api/slack_socket.py) and do not require HTTP endpoints.
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and return the FastAPI application."""
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
