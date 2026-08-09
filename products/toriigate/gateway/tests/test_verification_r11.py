"""Regressions for the R11 independent-verification findings.

An outside verifier re-checked the fixes from earlier rounds and found
most of them incomplete, plus 15 new issues. Each defect it demonstrated
gets a test here, so "fixed" means "provably fixed and kept fixed".
"""

import json
import warnings

import pytest

from toriigate import challenge as ch, logscan, netranges
from toriigate.core import Action, Category, RequestContext, resolve_client_ip
from toriigate.engine import Gateway
from toriigate.policy import Policy

warnings.simplefilter("ignore")
SECRET = b"r11-secret"
TRUSTED = ["10.0.0.0/8"]


def hdr(**kw):
    h = {"user-agent": "Mozilla/5.0 Chrome/126", "accept": "text/html",
         "accept-language": "ja", "accept-encoding": "gzip", "host": "x"}
    h.update(kw)
    return h


def ctx(path="/", ip="198.51.100.10", headers=None, method="GET", query=""):
    return RequestContext(method=method, path=path, client_ip=ip,
                          query=query, headers=headers or hdr())


# --- C-1(a): non-IP forwarded hop bypassed blocklist and rate limiting ---

@pytest.mark.parametrize("hop", ["x0", "notanip", "", "  ", "1.2.3", "::gg",
                                 "999.999.999.999", "<script>"])
def test_non_ip_forwarded_hop_falls_back_to_peer(hop):
    got = resolve_client_ip("10.0.0.5", {"x-forwarded-for": hop}, TRUSTED)
    assert got == "10.0.0.5", "garbage hop must not become the client identity"


def test_valid_forwarded_hop_still_honored():
    assert resolve_client_ip(
        "10.0.0.5", {"x-forwarded-for": "203.0.113.9"}, TRUSTED) == "203.0.113.9"


def test_proxy_chain_peeled_to_first_untrusted():
    assert resolve_client_ip(
        "10.0.0.5", {"x-forwarded-for": "203.0.113.9, 10.0.0.7"},
        TRUSTED) == "203.0.113.9"


def test_non_ip_hop_cannot_evade_blocklist():
    policy = Policy.from_dict({"trusted_proxies": TRUSTED,
                               "block_ips": ["203.0.113.0/24"]})
    gw = Gateway(policy=policy, secret=SECRET)
    ip = resolve_client_ip("203.0.113.9", {"x-forwarded-for": "junk"}, TRUSTED)
    assert gw.evaluate(ctx(ip=ip)).action == Action.BLOCK


# --- C-1(b): X-Real-IP accepted unvalidated -----------------------------

def test_x_real_ip_must_be_an_ip():
    assert resolve_client_ip(
        "10.0.0.5", {"x-real-ip": "not-an-ip"}, TRUSTED) == "10.0.0.5"


def test_x_real_ip_ignored_from_untrusted_peer():
    # The classic spoof: claim a Googlebot address from an untrusted peer.
    assert resolve_client_ip(
        "203.0.113.1", {"x-real-ip": "66.249.64.10"}, TRUSTED) == "203.0.113.1"


# --- C-2(a): pass cookie replaced the whole verdict with HUMAN ----------

def test_pass_cookie_does_not_launder_a_blocked_crawler():
    gw = Gateway(secret=SECRET)
    cookie = ch.make_pass_cookie(SECRET, "1.2.3.4", ttl=60)
    d = gw.evaluate(ctx(ip="1.2.3.4", headers=hdr(
        **{"user-agent": "GPTBot/1.2", "cookie": f"torii_pass={cookie}"})))
    assert d.action == Action.BLOCK
    assert d.verdict.category == Category.SPOOFED_BOT


def test_pass_cookie_still_exempts_from_challenge():
    # The legitimate benefit must survive: a solved challenge means you
    # are not challenged again.
    gw = Gateway(secret=SECRET)
    cookie = ch.make_pass_cookie(SECRET, "1.2.3.4", ttl=60)
    d = gw.evaluate(ctx(ip="1.2.3.4", headers=hdr(
        **{"user-agent": "curl/8.5.0", "cookie": f"torii_pass={cookie}"})))
    assert d.action == Action.ALLOW


# --- N-1: non-dict JSON to /_torii/verify raised AttributeError ---------

@pytest.mark.parametrize("body", [b"[]", b"1", b'"x"', b"null", b"true",
                                  b'{"token": 1, "nonce": []}', b"\xff\xfe"])
def test_verify_endpoint_rejects_hostile_bodies(body):
    gw = Gateway(secret=SECRET)
    resp = gw.handle_admin(
        ctx(path="/_torii/verify", method="POST", headers={}), body)
    assert resp.status in (400, 500) and resp is not None


# --- N-2: admin token compare crashed on non-ASCII (FUZZ-1 re-introduced)

@pytest.mark.parametrize("token", ["évil", "🙂", "\udc80", "x" * 500])
def test_admin_token_compare_survives_non_ascii(token):
    gw = Gateway(policy=Policy.from_dict({"admin_token": "s3cret"}),
                 secret=SECRET)
    resp = gw.handle_admin(
        ctx(path="/_torii/stats", headers={"x-torii-admin-token": token}), b"")
    assert resp.status == 401


def test_admin_token_still_accepts_correct_value():
    gw = Gateway(policy=Policy.from_dict({"admin_token": "s3cret"}),
                 secret=SECRET)
    resp = gw.handle_admin(
        ctx(path="/_torii/stats",
            headers={"x-torii-admin-token": "s3cret"}), b"")
    assert resp.status == 200


# --- N-3: unverifiable identity claims were allowed on the UA alone -----

UNVERIFIABLE = ["YouBot/1.0", "DuckDuckBot/1.1", "Claude-User/1.0",
                "MistralAI-User/1.0", "DuckAssistBot/1.0"]


@pytest.mark.parametrize("ua", UNVERIFIABLE)
def test_unverifiable_claim_costs_score(ua):
    gw = Gateway(secret=SECRET)
    d = gw.evaluate(ctx(ip="198.51.100.7", headers=hdr(**{"user-agent": ua})))
    assert any("unverifiable" in r for r in d.verdict.reasons)
    assert d.verdict.score >= 25


@pytest.mark.parametrize("ua", UNVERIFIABLE)
def test_require_verified_identity_downgrades_claim(ua):
    gw = Gateway(policy=Policy.from_dict({"require_verified_identity": True}),
                 secret=SECRET)
    d = gw.evaluate(ctx(ip="198.51.100.7", headers=hdr(**{"user-agent": ua})))
    assert d.action != Action.ALLOW
    assert d.verdict.category == Category.UNKNOWN_BOT


def test_verified_operator_unaffected_by_strict_mode():
    # GPTBot from a real OpenAI range still verifies normally.
    gw = Gateway(policy=Policy.from_dict({"require_verified_identity": True}),
                 secret=SECRET)
    d = gw.evaluate(ctx(ip="52.230.152.10",
                        headers=hdr(**{"user-agent": "GPTBot/1.2"})))
    assert d.verdict.verified is True
    assert d.verdict.category == Category.AI_TRAINING_CRAWLER


# --- N-10: monitor mode returned real 429s via the rate path ------------

def test_monitor_mode_never_throttles():
    import time
    gw = Gateway(policy=Policy.from_dict({
        "mode": "monitor", "allow_ips": ["198.51.100.0/24"],
        "rate_limit": {"max_requests": 3, "window_seconds": 10}}),
        secret=SECRET)
    base = time.time()
    actions = [gw.evaluate(ctx(ip="198.51.100.5", headers=hdr())).action
               for _ in range(6)]
    assert Action.THROTTLE not in actions
    assert actions[-1] in (Action.ALLOW, Action.LOG_ONLY)


# --- C-10: a syntactically valid but absurdly broad CIDR was accepted ---

def test_load_ranges_rejects_whole_internet(tmp_path):
    original = list(netranges.KNOWN_RANGES["openai"]["cidrs"])
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"openai": ["0.0.0.0/0"]}))
    try:
        with pytest.raises(ValueError):
            netranges.load_ranges(str(p))
        assert netranges.KNOWN_RANGES["openai"]["cidrs"] == original
    finally:
        netranges.KNOWN_RANGES["openai"]["cidrs"] = original
        netranges._parsed_cache.pop("openai", None)


def test_load_ranges_rejects_non_dict(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(["1.2.3.0/24"]))
    with pytest.raises(ValueError):
        netranges.load_ranges(str(p))


# --- FUZZ-2 continued: dict values of the wrong type crashed the scan ---

@pytest.mark.parametrize("line", [
    '{"ip": 1, "path": "/a", "user_agent": "x"}',
    '{"ip": "1.2.3.4", "path": 123, "user_agent": "x"}',
    '{"ip": "1.2.3.4", "path": "/a", "user_agent": 42}',
    '{"ip": ["1.2.3.4"], "path": "/a", "user_agent": "x"}',
    '{"ip": {"a": 1}, "path": {"b": 2}, "user_agent": null}',
])
def test_wrong_value_types_skipped_not_crashed(line):
    assert logscan._parse_json(line) is None
    res = logscan.scan([line], fmt="json")     # must not raise
    assert res.parsed == 0 and res.unparsed == 1


# --- N-6: ASGI had no request-body limit --------------------------------

def test_asgi_body_limit_enforced():
    import asyncio
    from toriigate.asgi import ToriiGateMiddleware

    async def app(scope, receive, send):  # pragma: no cover - not reached
        raise AssertionError("must not reach the app")

    mw = ToriiGateMiddleware(app, Gateway(secret=SECRET))
    chunk = b"x" * (1024 * 1024)
    sent = {"n": 0}

    async def receive():
        sent["n"] += 1
        return {"type": "http.request", "body": chunk, "more_body": True}

    messages = []

    async def send(m):
        messages.append(m)

    scope = {"type": "http", "method": "POST", "path": "/_torii/verify",
             "query_string": b"", "headers": [], "client": ("1.2.3.4", 1)}
    asyncio.run(mw(scope, receive, send))
    assert messages[0]["status"] == 413
