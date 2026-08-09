"""Regressions for bugs found by redteam/fuzz.py, plus a fuzz smoke run.

Every fuzz finding becomes a named test here so it can never come back —
that is what makes the review cycle compound instead of re-finding the
same defects.
"""

import base64
import warnings

import pytest

from toriigate import challenge as ch, logscan
from toriigate.core import RequestContext
from toriigate.engine import Gateway

SECRET = b"regression-secret"


def _decodable_payload() -> str:
    return base64.urlsafe_b64encode(
        b'{"ip":"1.2.3.4","exp":9999999999}').decode().rstrip("=")


# --- FUZZ-1: non-ASCII signature crashed hmac.compare_digest -------------
# Attacker-reachable on EVERY request via the torii_pass cookie → an
# unauthenticated DoS on the gateway's main path.

def test_non_ascii_pass_cookie_fails_closed():
    evil = f"{_decodable_payload()}.é"
    assert ch.check_pass_cookie(SECRET, evil, "1.2.3.4") is False


def test_non_ascii_challenge_token_fails_closed():
    evil = f"{_decodable_payload()}.é"
    assert ch.verify_solution(SECRET, evil, "0", "1.2.3.4") is False


def test_gateway_survives_malformed_cookie():
    gw = Gateway(secret=SECRET)
    evil = f"{_decodable_payload()}.é"
    ctx = RequestContext(
        method="GET", path="/", client_ip="1.2.3.4",
        headers={"user-agent": "Mozilla/5.0 Chrome/126", "host": "x",
                 "accept": "text/html", "accept-language": "ja",
                 "accept-encoding": "gzip",
                 "cookie": f"{ch.PASS_COOKIE}={evil}"})
    decision = gw.evaluate(ctx)          # must not raise
    assert decision.action.value == "allow"   # falls through to normal path


@pytest.mark.parametrize("bad", [
    "", ".", "..", "x", "x.", ".y", "é.é", "\x00.\x00",
    "!!!.!!!", "a" * 500 + ".b",
])
def test_assorted_malformed_cookies_fail_closed(bad):
    assert ch.check_pass_cookie(SECRET, bad, "1.2.3.4") is False
    assert ch.verify_solution(SECRET, bad, "0", "1.2.3.4") is False


def test_valid_cookie_still_accepted():
    # The hardening must not break the happy path.
    good = ch.make_pass_cookie(SECRET, "1.2.3.4", ttl=60)
    assert ch.check_pass_cookie(SECRET, good, "1.2.3.4") is True
    assert ch.check_pass_cookie(SECRET, good, "9.9.9.9") is False


# --- FUZZ-2: non-dict JSON log line crashed the scanner -----------------

@pytest.mark.parametrize("line", [
    "[1,2,3]", '"hello"', "123", "true", "false", "null", "[]",
])
def test_non_dict_json_log_lines_skipped(line):
    assert logscan._parse_json(line) is None


def test_scan_tolerates_mixed_garbage():
    lines = ['[1,2,3]', 'not json at all', '{}', 'true',
             '{"ip":"1.2.3.4","path":"/x","user_agent":"curl/8.5.0"}']
    res = logscan.scan(lines, fmt="json")
    assert res.parsed == 1              # only the real record
    assert res.unparsed == 4


# --- fuzz smoke: keep the harness itself honest -------------------------

def test_fuzz_harness_smoke():
    """Short run of every fuzz target, so CI catches a new fail-open."""
    from redteam import fuzz
    warnings.simplefilter("ignore")
    failures = []
    for target in fuzz.TARGETS:
        failures.extend(fuzz.run(target, iterations=300, seed=99))
    assert not failures, "\n".join(
        f"{f['target']} iter={f['iteration']}\n{f['trace']}" for f in failures)
