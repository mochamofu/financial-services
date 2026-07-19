"""ASGI middleware adapter — wrap any FastAPI / Starlette / Django ASGI app.

Usage::

    from toriigate import Gateway, Policy
    from toriigate.asgi import ToriiGateMiddleware

    app = ToriiGateMiddleware(app, Gateway(Policy.load("policy.yaml")))
"""

from __future__ import annotations

import asyncio
import time

from .core import OwnResponse, RequestContext, resolve_client_ip
from .engine import ADMIN_PREFIX, Gateway


class ToriiGateMiddleware:
    def __init__(self, app, gateway: Gateway | None = None):
        self.app = app
        self.gateway = gateway or Gateway()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        ctx = self._context(scope, self.gateway.policy.trusted_proxies)

        if ctx.path.startswith(ADMIN_PREFIX) or ctx.path == "/robots.txt":
            body = await self._read_body(receive)
            own = self.gateway.handle_admin(ctx, body)
            if own is not None:
                await self._send_own(send, own)
                return

        t0 = time.perf_counter()
        decision = self.gateway.evaluate(ctx)
        self.gateway.metrics.observe_latency(time.perf_counter() - t0)
        if decision.delay_seconds:
            await asyncio.sleep(decision.delay_seconds)
        if decision.response is not None:
            await self._send_own(send, decision.response)
            return

        verdict = decision.verdict

        async def send_tagged(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-toriigate-category",
                                verdict.category.value.encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_tagged)

    @staticmethod
    def _context(scope, trusted_proxies) -> RequestContext:
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers", [])}
        client = scope.get("client") or ("", 0)
        # Forwarded headers are only believed from a configured trusted
        # proxy; otherwise the socket peer is authoritative. Without this,
        # a client could set X-Real-IP to impersonate any address,
        # including verified-crawler ranges (redteam finding C-1).
        ip = resolve_client_ip(client[0] or "0.0.0.0", headers,
                               trusted_proxies)
        return RequestContext(
            method=scope.get("method", "GET"),
            path=scope.get("path", "/"),
            query=scope.get("query_string", b"").decode("latin-1"),
            client_ip=ip,
            headers=headers,
        )

    @staticmethod
    async def _read_body(receive) -> bytes:
        chunks = []
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        return b"".join(chunks)

    @staticmethod
    async def _send_own(send, own: OwnResponse):
        await send({
            "type": "http.response.start",
            "status": own.status,
            "headers": [(k.encode(), v.encode())
                        for k, v in own.headers.items()],
        })
        await send({"type": "http.response.body", "body": own.body})
