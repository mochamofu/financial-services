"""Standalone reverse-proxy mode — protect any existing site with one
command, no code changes and no CDN migration::

    python3 -m toriigate.proxy --origin http://localhost:3000 --port 8080

Stdlib only (ThreadingHTTPServer + urllib). Admin endpoints:
``/_torii/dashboard``, ``/_torii/stats``; ``/robots.txt`` is generated
from policy unless the origin should serve its own.
"""

from __future__ import annotations

import argparse
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import OwnResponse, RequestContext, resolve_client_ip
from .engine import ADMIN_PREFIX, Gateway
from .policy import Policy

HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate",
              "proxy-authorization", "te", "trailers",
              "transfer-encoding", "upgrade"}

# Headers the gateway sets itself: a client must never be able to inject
# these into the origin request by pre-supplying them (redteam C-6).
STRIP_FROM_CLIENT = {"x-forwarded-for", "x-real-ip",
                     "x-toriigate-category", "x-toriigate-action"}

MAX_BODY = 10 * 1024 * 1024        # cap request + origin response (C-8)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Return None so urllib passes the 3xx back instead of following it —
    an open redirect on the origin would otherwise let the gateway be
    used to fetch internal addresses server-side (redteam C-5)."""
    def redirect_request(self, *args, **kwargs):
        return None


_NO_REDIRECT = urllib.request.build_opener(_NoRedirect())


def make_handler(gateway: Gateway, origin: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # One implementation for every method.
        def _handle(self):
            headers = {k.lower(): v for k, v in self.headers.items()}
            path, _, query = self.path.partition("?")
            client_ip = resolve_client_ip(
                self.client_address[0], headers,
                gateway.policy.trusted_proxies)
            ctx = RequestContext(
                method=self.command, path=path, query=query,
                client_ip=client_ip, headers=headers)
            length = int(headers.get("content-length", 0) or 0)
            if length > MAX_BODY:
                return self._send_own(OwnResponse(
                    413, {"content-type": "text/plain"},
                    b"Payload too large.\n"))
            body = self.rfile.read(length) if length else b""

            if path.startswith(ADMIN_PREFIX) or path == "/robots.txt":
                own = gateway.handle_admin(ctx, body)
                if own is not None:
                    return self._send_own(own)

            t0 = time.perf_counter()
            decision = gateway.evaluate(ctx)
            gateway.metrics.observe_latency(time.perf_counter() - t0)
            if decision.delay_seconds:
                time.sleep(decision.delay_seconds)
            if decision.response is not None:
                return self._send_own(decision.response)
            self._forward(body, decision, client_ip)

        def _forward(self, body: bytes, decision, client_ip):
            url = origin.rstrip("/") + self.path
            fwd_headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in HOP_BY_HOP
                           and k.lower() != "host"
                           and k.lower() not in STRIP_FROM_CLIENT}
            fwd_headers["X-Forwarded-For"] = client_ip
            fwd_headers["X-ToriiGate-Category"] = (
                decision.verdict.category.value)
            req = urllib.request.Request(url, data=body or None,
                                         headers=fwd_headers,
                                         method=self.command)
            try:
                with _NO_REDIRECT.open(req, timeout=30) as resp:
                    payload = resp.read(MAX_BODY)
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() not in HOP_BY_HOP | {"content-length"}:
                            self.send_header(k, v)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
            except urllib.error.HTTPError as e:
                payload = e.read()
                self.send_response(e.code)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (urllib.error.URLError, OSError):
                payload = b"Bad gateway: origin unreachable.\n"
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        def _send_own(self, own: OwnResponse):
            self.send_response(own.status)
            for k, v in own.headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(own.body)))
            self.end_headers()
            self.wfile.write(own.body)

        def log_message(self, fmt, *args):  # quiet; events go to EventLog
            pass

    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD",
                   "OPTIONS"):
        setattr(Handler, f"do_{method}", Handler._handle)
    return Handler


def serve(origin: str, port: int = 8080, policy: Policy | None = None,
          host: str = "0.0.0.0") -> ThreadingHTTPServer:
    gateway = Gateway(policy=policy)
    server = ThreadingHTTPServer((host, port),
                                 make_handler(gateway, origin))
    server.gateway = gateway
    return server


def main(argv=None):
    import os
    ap = argparse.ArgumentParser(
        prog="toriigate-proxy",
        description="Put ToriiGate in front of an existing web origin.")
    ap.add_argument("--origin", default=os.environ.get("TORII_ORIGIN"),
                    help="Origin base URL, e.g. http://localhost:3000 "
                         "(or set TORII_ORIGIN)")
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("TORII_PORT", "8080")))
    ap.add_argument("--host", default=os.environ.get("TORII_HOST", "0.0.0.0"))
    ap.add_argument("--policy", default=os.environ.get("TORII_POLICY"),
                    help="Path to policy YAML/JSON (or set TORII_POLICY)")
    args = ap.parse_args(argv)
    if not args.origin:
        ap.error("--origin is required (or set TORII_ORIGIN)")
    policy = Policy.load(args.policy) if args.policy else None
    server = serve(args.origin, args.port, policy, args.host)
    print(f"ToriiGate proxy on http://{args.host}:{args.port} "
          f"-> {args.origin}")
    print(f"Dashboard: http://localhost:{args.port}{ADMIN_PREFIX}/dashboard")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
