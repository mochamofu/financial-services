import base64
import json
import time

from toriigate import challenge as ch

SECRET = b"test-secret"
IP = "198.51.100.10"


def test_pow_roundtrip():
    token = ch.make_challenge_token(SECRET, IP, difficulty=8)
    nonce = ch.solve(token, 8)
    assert nonce is not None
    assert ch.verify_solution(SECRET, token, nonce, IP)


def test_wrong_ip_rejected():
    token = ch.make_challenge_token(SECRET, IP, difficulty=8)
    nonce = ch.solve(token, 8)
    assert not ch.verify_solution(SECRET, token, nonce, "203.0.113.1")


def test_tampered_token_rejected():
    token = ch.make_challenge_token(SECRET, IP, difficulty=8)
    payload_b64, sig = token.split(".", 1)
    data = json.loads(ch._unb64(payload_b64))
    data["d"] = 1  # try to lower the difficulty
    forged = ch._b64(json.dumps(data).encode()) + "." + sig
    assert not ch.verify_solution(SECRET, forged, "0", IP)


def test_expired_challenge_rejected():
    payload = json.dumps({"ip": IP, "ts": int(time.time()) - 3600,
                          "d": 1, "n": "x"}).encode()
    token = ch._b64(payload) + "." + ch._sign(SECRET, payload)
    nonce = ch.solve(token, 1)
    assert not ch.verify_solution(SECRET, token, nonce, IP, max_age=600)


def test_pass_cookie_roundtrip():
    cookie = ch.make_pass_cookie(SECRET, IP, ttl=60)
    assert ch.check_pass_cookie(SECRET, cookie, IP)
    assert not ch.check_pass_cookie(SECRET, cookie, "203.0.113.1")
    assert not ch.check_pass_cookie(b"other-secret", cookie, IP)


def test_challenge_page_embeds_token():
    token = ch.make_challenge_token(SECRET, IP, difficulty=8)
    page = ch.challenge_page(token, 8).decode()
    assert token in page
    assert "/_torii/verify" in page
