"""Production-surface tests: metrics, health, threat-intel feed."""

from toriigate.core import Action, Category, RequestContext
from toriigate.engine import Gateway
from toriigate.metrics import Metrics
from toriigate import threatfeed

SECRET = b"ops-test"
BROWSER = {"user-agent": "Mozilla/5.0 Chrome/126", "accept": "text/html",
           "accept-language": "ja", "accept-encoding": "gzip",
           "host": "example.jp"}


def ctx(path="/", ip="198.51.100.10", headers=None):
    return RequestContext(method="GET", path=path, client_ip=ip,
                          headers=headers or dict(BROWSER))


# -- metrics -------------------------------------------------------------

def test_metrics_render_prometheus_format():
    m = Metrics()
    m.record("human", "allow")
    m.record("ai_training_crawler", "block")
    m.observe_latency(0.0003)
    out = m.render().decode()
    assert "toriigate_requests_total{category=\"human\",action=\"allow\"} 1" in out
    assert "toriigate_build_info" in out
    assert "toriigate_decision_latency_seconds_bucket" in out
    assert "toriigate_decision_latency_seconds_count 1" in out


def test_metrics_endpoint_served():
    gw = Gateway(secret=SECRET)
    gw.evaluate(ctx(headers={"user-agent": "ClaudeBot/1.0",
                             "host": "example.jp"}))
    resp = gw.handle_admin(ctx(path="/_torii/metrics"), b"")
    assert resp.status == 200
    assert b"toriigate_requests_total" in resp.body
    assert b'action="block"' in resp.body


def test_health_endpoints():
    gw = Gateway(secret=SECRET)
    for p in ("/_torii/healthz", "/_torii/readyz"):
        resp = gw.handle_admin(ctx(path=p), b"")
        assert resp.status == 200
        assert b"ok" in resp.body


def test_metrics_gated_by_admin_token():
    from toriigate.policy import Policy
    gw = Gateway(policy=Policy.from_dict({"admin_token": "t"}), secret=SECRET)
    assert gw.handle_admin(ctx(path="/_torii/metrics"), b"").status == 401


# -- threat-intel feed ---------------------------------------------------

def test_refresh_parses_prefix_feeds():
    def fake_fetch(url):
        return {"prefixes": [{"ipv4Prefix": "203.0.113.0/24"},
                             {"ipv4Prefix": "198.51.100.0/24"}]}
    src = [threatfeed.Source("openai", "http://x",
                             threatfeed._parse_prefixes)]
    data = threatfeed.refresh(sources=src, fetch=fake_fetch)
    assert data["openai"] == ["203.0.113.0/24", "198.51.100.0/24"]
    assert "cidrs" in data["_report"]["openai"]


def test_refresh_keeps_previous_on_failure():
    def broken_fetch(url):
        raise RuntimeError("network down")
    src = [threatfeed.Source("openai", "http://x",
                             threatfeed._parse_prefixes)]
    data = threatfeed.refresh(sources=src, fetch=broken_fetch,
                              previous={"openai": ["1.2.3.0/24"]})
    assert data["openai"] == ["1.2.3.0/24"]        # not blanked
    assert "KEPT PREVIOUS" in data["_report"]["openai"]


def test_refresh_drops_invalid_cidrs():
    def fetch(url):
        return {"prefixes": [{"ipv4Prefix": "203.0.113.0/24"},
                             {"ipv4Prefix": "not-a-cidr"}]}
    src = [threatfeed.Source("openai", "http://x",
                             threatfeed._parse_prefixes)]
    data = threatfeed.refresh(sources=src, fetch=fetch)
    assert data["openai"] == ["203.0.113.0/24"]


def test_write_atomic_roundtrip(tmp_path):
    import json
    out = tmp_path / "ranges.json"
    threatfeed.write_atomic(str(out), {"openai": ["1.2.3.0/24"],
                                       "_report": {"x": "y"}})
    loaded = json.loads(out.read_text())
    assert loaded == {"openai": ["1.2.3.0/24"]}    # _report stripped


def test_loaded_ranges_used_for_verification(tmp_path):
    # End-to-end: a refreshed feed changes anti-spoofing behavior.
    import json
    from toriigate import netranges
    from toriigate.scoring import Detector
    original = list(netranges.KNOWN_RANGES["openai"]["cidrs"])
    out = tmp_path / "r.json"
    out.write_text(json.dumps({"openai": ["10.0.0.0/8"]}))
    netranges.load_ranges(str(out))
    try:
        v = Detector().classify(RequestContext(
            method="GET", path="/", client_ip="10.1.2.3",
            headers={"user-agent": "GPTBot/1.2"}))
        assert v.verified is True     # now inside the refreshed range
    finally:
        # restore the seed so other tests see the original ranges
        netranges.KNOWN_RANGES["openai"]["cidrs"] = original
        netranges._parsed_cache.pop("openai", None)
