import time

from toriigate import challenge as ch
from toriigate.core import Action, Category, RequestContext
from toriigate.engine import Gateway
from toriigate.policy import Policy

SECRET = b"engine-test-secret"
BROWSER_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0",
    "accept": "text/html", "accept-language": "ja",
    "accept-encoding": "gzip", "host": "example.jp",
}


def ctx(path="/", ip="198.51.100.10", headers=None, ts=None):
    return RequestContext(method="GET", path=path, client_ip=ip,
                          headers=headers or dict(BROWSER_HEADERS),
                          ts=ts or time.time())


def test_training_crawler_blocked_with_403():
    gw = Gateway(secret=SECRET)
    d = gw.evaluate(ctx(headers={"user-agent": "ClaudeBot/1.0",
                                 "host": "example.jp"}))
    assert d.action == Action.BLOCK
    assert d.response.status == 403
    assert b"ToriiGate" in d.response.body


def test_scraper_gets_challenge_page():
    gw = Gateway(secret=SECRET)
    d = gw.evaluate(ctx(headers={"user-agent": "curl/8.5.0",
                                 "host": "example.jp"}))
    assert d.action == Action.CHALLENGE
    assert d.response.status == 403
    assert b"/_torii/verify" in d.response.body


def test_human_passes_through():
    gw = Gateway(secret=SECRET)
    d = gw.evaluate(ctx())
    assert d.action == Action.ALLOW
    assert d.passed


def test_pass_cookie_skips_detection():
    gw = Gateway(secret=SECRET)
    cookie = ch.make_pass_cookie(SECRET, "198.51.100.10", ttl=60)
    headers = {"user-agent": "curl/8.5.0", "host": "example.jp",
               "cookie": f"{ch.PASS_COOKIE}={cookie}"}
    d = gw.evaluate(ctx(headers=headers))
    assert d.action == Action.ALLOW


def test_verify_endpoint_full_flow():
    gw = Gateway(secret=SECRET)
    challenged = gw.evaluate(ctx(headers={"user-agent": "curl/8.5.0",
                                          "host": "example.jp"}))
    body = challenged.response.body.decode()
    token = body.split("const token = ")[1].split(",")[0].strip("'\"")
    nonce = ch.solve(token, gw.policy.challenge_difficulty)
    post = RequestContext(method="POST", path="/_torii/verify",
                          client_ip="198.51.100.10",
                          headers={"host": "example.jp"})
    resp = gw.handle_admin(
        post, f'{{"token": "{token}", "nonce": "{nonce}"}}'.encode())
    assert resp.status == 200
    assert ch.PASS_COOKIE in resp.headers["set-cookie"]


def test_rate_limit_throttles_humans():
    policy = Policy.from_dict({"rate_limit": {"max_requests": 5,
                                              "window_seconds": 10}})
    gw = Gateway(policy=policy, secret=SECRET)
    base = time.time()
    decisions = [gw.evaluate(ctx(ts=base + i * 0.01)) for i in range(8)]
    assert decisions[0].action == Action.ALLOW
    assert decisions[-1].action == Action.THROTTLE
    assert decisions[-1].response.status == 429


def test_monetize_returns_402():
    policy = Policy.from_dict({
        "category_actions": {"ai_training_crawler": "monetize"},
        "monetize": {"price_usd_per_1k": 2.5}})
    gw = Gateway(policy=policy, secret=SECRET)
    d = gw.evaluate(ctx(headers={"user-agent": "ClaudeBot/1.0",
                                 "host": "example.jp"}))
    assert d.action == Action.MONETIZE
    assert d.response.status == 402
    assert b"2.5" in d.response.body


def test_events_recorded():
    gw = Gateway(secret=SECRET)
    gw.evaluate(ctx(headers={"user-agent": "ClaudeBot/1.0",
                             "host": "example.jp"}))
    gw.evaluate(ctx())
    snap = gw.events.snapshot()
    assert snap["total_requests"] == 2
    assert snap["by_category"][Category.AI_TRAINING_CRAWLER.value] == 1
    assert snap["actions_taken"] == 1


def test_stats_endpoint_json():
    gw = Gateway(secret=SECRET)
    resp = gw.handle_admin(ctx(path="/_torii/stats"), b"")
    assert resp.status == 200
    assert b"total_requests" in resp.body


def test_robots_txt_generated():
    gw = Gateway(secret=SECRET)
    resp = gw.handle_admin(ctx(path="/robots.txt"), b"")
    assert resp.status == 200
    assert b"GPTBot" in resp.body


def test_unknown_nonbrowser_ua_is_challenged():
    # V-1: a UA that is neither a known signature nor browser-shaped must
    # not sail through as HUMAN.
    gw = Gateway(secret=SECRET)
    d = gw.evaluate(ctx(headers={"user-agent": "Acme-Fetcher/1.0",
                                 "host": "example.jp"}))
    assert d.action == Action.CHALLENGE
    assert d.verdict.category == Category.UNKNOWN_BOT


def test_pass_cookie_does_not_bypass_honeypot():
    # C-2: a solved-challenge cookie is not a licence to probe traps.
    gw = Gateway(secret=SECRET)
    cookie = ch.make_pass_cookie(SECRET, "198.51.100.10", ttl=60)
    headers = {"user-agent": "Mozilla/5.0", "host": "example.jp",
               "cookie": f"{ch.PASS_COOKIE}={cookie}"}
    d = gw.evaluate(ctx(path="/.well-known/torii-trap", headers=headers))
    assert d.action == Action.BLOCK
    assert d.verdict.category == Category.MALICIOUS


def test_pass_cookie_still_rate_limited():
    # C-2: a cookie holder is still subject to the rate limit.
    policy = Policy.from_dict({"rate_limit": {"max_requests": 5,
                                              "window_seconds": 10}})
    gw = Gateway(policy=policy, secret=SECRET)
    cookie = ch.make_pass_cookie(SECRET, "198.51.100.10", ttl=60)
    headers = {"user-agent": "Mozilla/5.0 Chrome/126", "host": "example.jp",
               "cookie": f"{ch.PASS_COOKIE}={cookie}"}
    base = time.time()
    decisions = [gw.evaluate(ctx(headers=headers, ts=base + i * 0.01))
                 for i in range(8)]
    assert decisions[0].action == Action.ALLOW
    assert decisions[-1].action == Action.THROTTLE


def test_admin_stats_requires_token_when_configured():
    # C-7: stats endpoint gated behind admin token when set.
    policy = Policy.from_dict({"admin_token": "s3cr3t"})
    gw = Gateway(policy=policy, secret=SECRET)
    assert gw.handle_admin(ctx(path="/_torii/stats"), b"").status == 401
    ok = gw.handle_admin(
        RequestContext(method="GET", path="/_torii/stats",
                       client_ip="198.51.100.10",
                       headers={"x-torii-admin-token": "s3cr3t"}), b"")
    assert ok.status == 200
