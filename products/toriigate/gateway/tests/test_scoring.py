import time

from toriigate.core import Category, RequestContext
from toriigate.scoring import Detector

BROWSER_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0",
    "accept": "text/html",
    "accept-language": "ja,en;q=0.8",
    "accept-encoding": "gzip",
}


def ctx(path="/", ip="198.51.100.10", headers=None, ts=None):
    return RequestContext(method="GET", path=path, client_ip=ip,
                          headers=headers or dict(BROWSER_HEADERS),
                          ts=ts or time.time())


def test_human_browser_low_score():
    v = Detector().classify(ctx())
    assert v.category == Category.HUMAN
    assert v.score <= 10


def test_spoofed_gptbot_flagged():
    v = Detector().classify(ctx(
        ip="203.0.113.5", headers={"user-agent": "GPTBot/1.2"}))
    assert v.category == Category.SPOOFED_BOT
    assert v.score >= 90


def test_genuine_gptbot_verified():
    v = Detector().classify(ctx(
        ip="52.230.152.10", headers={"user-agent": "GPTBot/1.2"}))
    assert v.category == Category.AI_TRAINING_CRAWLER
    assert v.verified is True


def test_unverifiable_operator_not_spoofed():
    # ClaudeBot has no published range set in the seed data: never
    # marked spoofed on IP alone.
    v = Detector().classify(ctx(
        ip="203.0.113.5", headers={"user-agent": "ClaudeBot/1.0"}))
    assert v.category == Category.AI_TRAINING_CRAWLER
    assert v.verified is None


def test_browser_claim_without_browser_headers():
    v = Detector().classify(ctx(headers={
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64)"}))
    assert v.category == Category.UNKNOWN_BOT


def test_honeypot_marks_offender_and_raises_next_score():
    d = Detector()
    first = d.classify(ctx(path="/.well-known/torii-trap"))
    assert first.category == Category.MALICIOUS
    again = d.classify(ctx(path="/normal"))
    assert any("prior offense" in r for r in again.reasons)
    assert again.score > 5


def test_rate_burst_turns_human_into_bot():
    d = Detector(rate_suspicious=10)
    base = time.time()
    verdicts = [d.classify(ctx(ts=base + i * 0.01)) for i in range(30)]
    assert verdicts[0].category == Category.HUMAN
    assert verdicts[-1].category == Category.UNKNOWN_BOT
