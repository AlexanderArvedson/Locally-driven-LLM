"""Unit tests for the FastAPI Slack endpoints.

No live services required — TaskQueue.enqueue is mocked and signature
headers are generated locally using the same HMAC logic as the verifier.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.scheduler.task import PipelineTask, QueryTask


_SECRET = "test-signing-secret"
_REPO = "test-repo"


def _make_headers(body: bytes, secret: str = _SECRET, ts_offset: int = 0) -> dict:
    """Generate valid X-Slack-Signature and X-Slack-Request-Timestamp headers."""
    ts = str(int(time.time()) + ts_offset)
    sig_base = f"v0:{ts}:{body.decode()}"
    sig = "v0=" + hmac.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    return {"X-Slack-Signature": sig, "X-Slack-Request-Timestamp": ts}


def _make_app(enqueue_mock: AsyncMock | None = None):
    queue = MagicMock()
    queue.enqueue = enqueue_mock or AsyncMock()
    return create_app(queue=queue, signing_secret=_SECRET, repo_name=_REPO), queue


# ---------------------------------------------------------------------------
# /slack/query
# ---------------------------------------------------------------------------


def test_query_missing_signature_returns_403():
    app, _ = _make_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/slack/query", data={"text": "auth", "response_url": "http://x"})
    assert resp.status_code == 403


def test_query_invalid_signature_returns_403():
    app, _ = _make_app()
    body = b"text=auth&response_url=http%3A%2F%2Fx"
    headers = _make_headers(body, secret="wrong-secret")
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/slack/query", content=body, headers={**headers, "Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == 403


def test_query_replay_attack_returns_403():
    app, _ = _make_app()
    body = b"text=auth&response_url=http%3A%2F%2Fx"
    # timestamp 6 minutes in the past — outside the 5-minute window
    headers = _make_headers(body, ts_offset=-360)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/slack/query", content=body, headers={**headers, "Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == 403


def test_query_valid_signature_returns_200_and_enqueues():
    enqueue = AsyncMock()
    app, queue = _make_app(enqueue)
    body = b"text=find+auth+functions&response_url=http%3A%2F%2Fslack.example.com%2Fresponse"
    headers = _make_headers(body)
    with TestClient(app) as client:
        resp = client.post(
            "/slack/query",
            content=body,
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_type"] == "ephemeral"
    assert data["text"] == "Searching..."

    enqueue.assert_called_once()
    task: QueryTask = enqueue.call_args.args[0]
    assert isinstance(task, QueryTask)
    assert task.query_text == "find auth functions"
    assert task.response_url == "http://slack.example.com/response"
    assert task.repo == _REPO


# ---------------------------------------------------------------------------
# /slack/pipeline
# ---------------------------------------------------------------------------


def test_pipeline_missing_signature_returns_403():
    app, _ = _make_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/slack/pipeline", data={})
    assert resp.status_code == 403


def test_pipeline_valid_signature_returns_200_and_enqueues():
    enqueue = AsyncMock()
    app, _ = _make_app(enqueue)
    body = b""
    headers = _make_headers(body)
    with TestClient(app) as client:
        resp = client.post(
            "/slack/pipeline",
            content=body,
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Pipeline run queued."

    enqueue.assert_called_once()
    task: PipelineTask = enqueue.call_args.args[0]
    assert isinstance(task, PipelineTask)
    assert task.repo == _REPO
    assert task.no_descriptions is False


def test_pipeline_no_descriptions_flag():
    enqueue = AsyncMock()
    app, _ = _make_app(enqueue)
    body = b"no_descriptions=1"
    headers = _make_headers(body)
    with TestClient(app) as client:
        client.post(
            "/slack/pipeline",
            content=body,
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        )
    task: PipelineTask = enqueue.call_args.args[0]
    assert task.no_descriptions is True
