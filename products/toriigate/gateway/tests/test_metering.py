from toriigate.core import RequestContext
from toriigate.engine import Gateway
from toriigate.metering import UsageMeter
from toriigate.policy import Policy

BROWSER = {"user-agent": "Mozilla/5.0 Chrome/126", "accept": "text/html",
           "accept-language": "ja", "accept-encoding": "gzip",
           "host": "example.jp"}


def test_meter_counts_per_tenant():
    m = UsageMeter(period="2026-07")
    m.record("acme", "allow")
    m.record("acme", "block")
    m.record("beta", "allow")
    assert m.usage("acme").analyzed_requests == 2
    assert m.usage("acme").by_action == {"allow": 1, "block": 1}
    assert m.usage("beta").analyzed_requests == 1
    assert m.usage("unknown").analyzed_requests == 0


def test_meter_export_billing_shape():
    m = UsageMeter(period="2026-07")
    for _ in range(3):
        m.record("acme", "allow")
    export = m.export()
    assert export == [{"tenant": "acme", "period": "2026-07",
                       "analyzed_requests": 3}]


def test_gateway_meters_evaluations():
    gw = Gateway(policy=Policy.from_dict({"tenant": "acme"}), secret=b"s")
    gw.evaluate(RequestContext(method="GET", path="/", client_ip="198.51.100.1",
                               headers=dict(BROWSER)))
    gw.evaluate(RequestContext(method="GET", path="/", client_ip="203.0.113.9",
                               headers={"user-agent": "ClaudeBot/1.0",
                                        "host": "example.jp"}))
    snap = gw.meter.snapshot()
    assert snap["tenants"]["acme"]["analyzed_requests"] == 2
    assert snap["tenants"]["acme"]["by_action"]["block"] == 1


def test_usage_endpoint_admin_gated():
    gw = Gateway(policy=Policy.from_dict({"admin_token": "t"}), secret=b"s")
    ctx = RequestContext(method="GET", path="/_torii/usage",
                         client_ip="198.51.100.1", headers={})
    assert gw.handle_admin(ctx, b"").status == 401
    ok = RequestContext(method="GET", path="/_torii/usage",
                        client_ip="198.51.100.1",
                        headers={"x-torii-admin-token": "t"})
    assert gw.handle_admin(ok, b"").status == 200
