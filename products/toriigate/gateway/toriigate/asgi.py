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

MAX_BODY = 10 * 1024 * 1024


class _BodyTooLarge(Exception):
    """Raised when a request body exceeds MAX_BODY."""


def _replay_receive(body: bytes):
    """A `receive` callable that yields an already-consumed body once."""
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


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
            try:
                body = await self._read_body(receive)
            except _BodyTooLarge:
                await self._send_own(send, OwnResponse(
                    413, {"content-type": "text/plain"},
                    b"Payload too large.\n"))
                return
            own = self.gateway.handle_admin(ctx, body)
            if own is not None:
                await self._send_own(send, own)
                return
            # handle_admin declined. The receive channel is already drained,
            # so hand the app a replay of the body — otherwise the request
            # hangs waiting for a message that will never come (N-14).
            receive = _replay_receive(body)

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
        ip = resolve_client_ip(
            client[0] or "0.0.0.0",  # nosec B104 — unknown-peer placeholder
            headers, trusted_proxies)
        return RequestContext(
            method=scope.get("method", "GET"),
            path=scope.get("path", "/"),
            query=scope.get("query_string", b"").decode("latin-1"),
            client_ip=ip,
            headers=headers,
        )

    @staticmethod
    async def _read_body(receive, max_bytes: int = MAX_BODY) -> bytes:
        # Bounded: the admin paths read the whole body into memory, and
        # ASGI servers do not cap it by default, so an unauthenticated
        # POST could exhaust memory (finding N-6).
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > max_bytes:
                raise _BodyTooLarge()
            chunks.append(chunk)
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
