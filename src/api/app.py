"""FastAPI application for the Slack integration.

Creates and configures the app with Slack slash command endpoints and
HMAC-SHA256 request signature verification.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from src.scheduler.queue import TaskQueue
from src.scheduler.task import PipelineTask, QueryTask

_TIMESTAMP_MAX_AGE_SECONDS = 300


def _make_signature_verifier(signing_secret: str):
    """Return a FastAPI dependency that validates X-Slack-Signature on every request.

    Reads and caches request.body() so the route handler can still read
    form data from the cached body via request.form().
    """

    async def verify(
        request: Request,
        x_slack_signature: Annotated[str | None, Header()] = None,
        x_slack_request_timestamp: Annotated[str | None, Header()] = None,
    ) -> None:
        if not x_slack_signature or not x_slack_request_timestamp:
            raise HTTPException(status_code=403, detail="Missing Slack signature headers")

        try:
            ts = int(x_slack_request_timestamp)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid timestamp")

        if abs(time.time() - ts) > _TIMESTAMP_MAX_AGE_SECONDS:
            raise HTTPException(status_code=403, detail="Request timestamp too old")

        # Cache the raw body so request.form() can still read it afterwards.
        body = await request.body()
        sig_base = f"v0:{ts}:{body.decode()}"
        expected = (
            "v0="
            + hmac.new(
                signing_secret.encode(),
                sig_base.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        if not hmac.compare_digest(expected, x_slack_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    return verify


def create_app(queue: TaskQueue, signing_secret: str, repo_name: str) -> FastAPI:
    """Create and return the FastAPI application.

    Args:
        queue: The shared task queue that slash command handlers enqueue work into.
        signing_secret: Slack signing secret used to verify request authenticity.
        repo_name: Default repository name attached to enqueued tasks.
    """
    app = FastAPI()
    verify_signature = _make_signature_verifier(signing_secret)

    @app.post("/slack/query", dependencies=[Depends(verify_signature)])
    async def slack_query(request: Request) -> dict:
        """Receive a /query slash command and enqueue a QueryTask."""
        form = await request.form()
        task = QueryTask(
            id=str(uuid.uuid4()),
            query_text=str(form.get("text", "")),
            response_url=str(form.get("response_url", "")),
            repo=repo_name,
        )
        await queue.enqueue(task)
        return {"response_type": "ephemeral", "text": "Searching..."}

    @app.post("/slack/pipeline", dependencies=[Depends(verify_signature)])
    async def slack_pipeline(request: Request) -> dict:
        """Receive a /pipeline slash command and enqueue a PipelineTask."""
        form = await request.form()
        task = PipelineTask(
            id=str(uuid.uuid4()),
            repo=repo_name,
            no_descriptions=bool(form.get("no_descriptions")),
        )
        await queue.enqueue(task)
        return {"text": "Pipeline run queued."}

    return app
