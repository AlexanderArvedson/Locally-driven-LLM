"""Unit tests for the FastAPI health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_health_returns_ok():
    with TestClient(create_app()) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
