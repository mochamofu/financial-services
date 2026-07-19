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

from .core import OwnResponse, RequestContext
from .engine import ADMIN_PREFIX, Gateway
from .policy import Policy

HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate",
              "proxy-authorization", "te", "trailers",
              "transfer-encoding", "upgrade"}


def make_handler(gateway: Gateway, origin: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # One implementation for every method.
        def _handle(self):
            headers = {k.lower(): v for k, v in self.headers.items()}
            path, _, query = self.path.partition("?")
            ctx = RequestContext(
                method=self.command, path=path, query=query,
                client_ip=self.client_address[0], headers=headers)
            length = int(headers.get("content-length", 0) or 0)
            body = self.rfile.read(length) if length else b""

            if path.startswith(ADMIN_PREFIX) or path == "/robots.txt":
                own = gateway.handle_admin(ctx, body)
                if own is not None:
                    return self._send_own(own)

            decision = gateway.evaluate(ctx)
            if decision.delay_seconds:
                time.sleep(decision.delay_seconds)
            if decision.response is not None:
                return self._send_own(decision.response)
            self._forward(body, decision)

        def _forward(self, body: bytes, decision):
            url = origin.rstrip("/") + self.path
            fwd_headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in HOP_BY_HOP
                           and k.lower() != "host"}
            fwd_headers["X-Forwarded-For"] = self.client_address[0]
            fwd_headers["X-ToriiGate-Category"] = (
                decision.verdict.category.value)
            req = urllib.request.Request(url, data=body or None,
                                         headers=fwd_headers,
                                         method=self.command)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    payload = resp.read()
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
    ap = argparse.ArgumentParser(
        prog="toriigate-proxy",
        description="Put ToriiGate in front of an existing web origin.")
    ap.add_argument("--origin", required=True,
                    help="Origin base URL, e.g. http://localhost:3000")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--policy", help="Path to policy YAML/JSON")
    args = ap.parse_args(argv)
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
