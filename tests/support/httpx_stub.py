from contextlib import contextmanager
import sys
import types
from typing import Any


@contextmanager
def httpx_stub():
    """Temporarily insert a minimal `httpx` stub into sys.modules.

    Use in tests that import modules which instantiate an `httpx.AsyncClient`.
    The stub is removed after the context exits.
    """
    inserted = False
    if sys.modules.get("httpx") is None:
        dummy = types.ModuleType("httpx")

        class _DummyAsyncClient:
            def __init__(self, timeout=None):
                pass

            async def post(self, *args, **kwargs):
                class _Resp:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {"message": {"content": ""}}

                return _Resp()

            async def aclose(self):
                return None

        httpx_mod: Any = dummy
        httpx_mod.AsyncClient = _DummyAsyncClient
        httpx_mod.HTTPError = Exception
        httpx_mod.HTTPStatusError = type("HTTPStatusError", (), {})
        sys.modules["httpx"] = dummy
        inserted = True

    try:
        yield
    finally:
        if inserted:
            sys.modules.pop("httpx", None)
