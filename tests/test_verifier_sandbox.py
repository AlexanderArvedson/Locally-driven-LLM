import os
import pytest
from typing import cast

from src.graph.nodes.verifier import verifier_node
from src.observability.context import RunContext
from src.graph.state import GraphState


@pytest.mark.asyncio
async def test_verifier_uses_sandbox(monkeypatch):
    monkeypatch.setenv("VERIFIER_USE_SUBPROCESS", "1")

    state = cast(GraphState, {"generated_code": "print('hello-sandbox')"})

    res = await verifier_node(state, RunContext.new())
    assert res["verification_passed"] is True
