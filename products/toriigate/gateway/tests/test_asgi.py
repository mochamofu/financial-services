import asyncio

from toriigate.asgi import ToriiGateMiddleware
from toriigate.engine import Gateway

BROWSER_HEADERS = [
    (b"user-agent", b"Mozilla/5.0 (Windows NT 10.0) Chrome/126.0"),
    (b"accept", b"text/html"), (b"accept-language", b"ja"),
    (b"accept-encoding", b"gzip"), (b"host", b"example.jp"),
]


async def hello_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": b"hello"})


def run(app, path="/", headers=None, method="GET", client_ip="198.51.100.30"):
    scope = {"type": "http", "method": method, "path": path,
             "query_string": b"", "headers": headers or BROWSER_HEADERS,
             "client": (client_ip, 12345)}
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    return messages


def test_human_passes_and_gets_tag_header():
    app = ToriiGateMiddleware(hello_app, Gateway(secret=b"s"))
    messages = run(app)
    start = messages[0]
    assert start["status"] == 200
    headers = dict(start["headers"])
    assert headers[b"x-toriigate-category"] == b"human"
    assert messages[1]["body"] == b"hello"


def test_training_crawler_blocked_before_app():
    called = []

    async def origin(scope, receive, send):
        called.append(True)
        await hello_app(scope, receive, send)

    app = ToriiGateMiddleware(origin, Gateway(secret=b"s"))
    messages = run(app, headers=[(b"user-agent", b"GPTBot/1.2"),
                                 (b"host", b"example.jp")],
                   client_ip="203.0.113.9")  # outside OpenAI ranges: spoofed
    assert messages[0]["status"] == 403
    assert not called


def test_stats_endpoint_served_by_middleware():
    app = ToriiGateMiddleware(hello_app, Gateway(secret=b"s"))
    messages = run(app, path="/_torii/stats")
    assert messages[0]["status"] == 200
    assert b"total_requests" in messages[1]["body"]
