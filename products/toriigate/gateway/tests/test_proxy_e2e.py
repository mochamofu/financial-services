"""End-to-end: real origin server + real ToriiGate proxy over sockets."""

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from toriigate.proxy import serve

BROWSER_UA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0",
    "Accept": "text/html", "Accept-Language": "ja",
    "Accept-Encoding": "identity",
}


class OriginHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"origin says hi from " + self.path.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


@pytest.fixture(scope="module")
def stack():
    import os
    os.environ.setdefault("TORII_SECRET", "e2e-stable-secret")
    origin = ThreadingHTTPServer(("127.0.0.1", 0), OriginHandler)
    threading.Thread(target=origin.serve_forever, daemon=True).start()
    origin_url = f"http://127.0.0.1:{origin.server_address[1]}"

    proxy = serve(origin_url, port=0, host="127.0.0.1")
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    proxy_url = f"http://127.0.0.1:{proxy.server_address[1]}"

    yield proxy_url
    proxy.shutdown()
    origin.shutdown()


def get(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout)


def test_browser_request_reaches_origin(stack):
    with get(f"{stack}/page", BROWSER_UA_HEADERS) as resp:
        assert resp.status == 200
        assert b"origin says hi from /page" in resp.read()


def test_ai_training_crawler_blocked_at_proxy(stack):
    with pytest.raises(urllib.error.HTTPError) as exc:
        get(f"{stack}/page", {"User-Agent": "ClaudeBot/1.0",
                              "Accept-Encoding": "identity"})
    assert exc.value.code == 403


def test_scraper_receives_challenge(stack):
    with pytest.raises(urllib.error.HTTPError) as exc:
        get(f"{stack}/data", {"User-Agent": "python-requests/2.32",
                              "Accept-Encoding": "identity"})
    assert exc.value.code == 403
    assert b"/_torii/verify" in exc.value.read()


def test_robots_txt_generated_at_edge(stack):
    with get(f"{stack}/robots.txt", BROWSER_UA_HEADERS) as resp:
        text = resp.read().decode()
    assert "User-agent: GPTBot" in text
    assert "Disallow: /.well-known/torii-trap" in text


def test_stats_reflect_traffic(stack):
    with get(f"{stack}/_torii/stats", BROWSER_UA_HEADERS) as resp:
        stats = json.loads(resp.read())
    assert stats["total_requests"] >= 2
    assert stats["by_action"].get("block", 0) >= 1


def test_dashboard_serves_html(stack):
    with get(f"{stack}/_torii/dashboard", BROWSER_UA_HEADERS) as resp:
        assert b"ToriiGate" in resp.read()
