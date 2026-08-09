"""Proof-of-work challenge: imposes a per-challenge CPU cost that is
invisible to a human but taxes large-scale automated crawling.

Cost scales as ~2**difficulty SHA-256 tries. At the default difficulty
of 16 that is ~50-110ms of CPU per challenge; raise it for a stiffer
tax. Note this is a *cost*, not a wall — a determined scraper with cheap
compute can still solve it, and does not need a browser to do so (see
``solve``). Pair it with identity/behavior signals and a short
``challenge_ttl`` rather than relying on it alone.

Flow:
1. Gateway responds 403 with an interstitial page + signed challenge token.
2. Browser JS brute-forces a nonce so SHA-256(token:nonce) has N leading
   zero bits, then POSTs it to /_torii/verify.
3. Gateway validates and sets a signed ``torii_pass`` cookie; subsequent
   requests skip identity detection (but not trap or rate checks) until
   the cookie expires.

Everything is HMAC-signed with the gateway secret; no server-side
session storage is needed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

PASS_COOKIE = "torii_pass"  # nosec B105 — cookie name, not a secret


def _sign(secret: bytes, payload: bytes) -> str:
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def make_challenge_token(secret: bytes, client_ip: str,
                         difficulty: int) -> str:
    payload = json.dumps({
        "ip": client_ip, "ts": int(time.time()),
        "d": difficulty, "n": _b64(os.urandom(8)),
    }).encode()
    return _b64(payload) + "." + _sign(secret, payload)


def _leading_zero_bits(digest: bytes) -> int:
    bits = 0
    for byte in digest:
        if byte == 0:
            bits += 8
            continue
        for shift in range(7, -1, -1):
            if byte >> shift & 1:
                return bits
            bits += 1
    return bits


def sig_matches(sig: str, expected: str) -> bool:
    """Constant-time compare that tolerates hostile input.

    ``hmac.compare_digest`` raises TypeError on str arguments containing
    non-ASCII, and both the challenge token and the pass cookie are fully
    attacker-controlled — so comparing as str turns a malformed cookie
    into an uncaught exception on every request (found by redteam/fuzz).
    Encoding to bytes keeps the comparison constant-time and makes a bad
    signature simply not match.
    """
    return hmac.compare_digest(sig.encode("utf-8", "surrogatepass"),
                               expected.encode())


def verify_solution(secret: bytes, token: str, nonce: str,
                    client_ip: str, max_age: int = 600) -> bool:
    try:
        payload_b64, sig = token.split(".", 1)
        payload = _unb64(payload_b64)
        if not sig_matches(sig, _sign(secret, payload)):
            return False
        data = json.loads(payload)
        if data["ip"] != client_ip or time.time() - data["ts"] > max_age:
            return False
        digest = hashlib.sha256(f"{token}:{nonce}".encode()).digest()
        return _leading_zero_bits(digest) >= data["d"]
    except (ValueError, TypeError, KeyError, UnicodeError):
        # Fail closed: any malformed token is simply not a valid solution.
        return False


def solve(token: str, difficulty: int, limit: int = 5_000_000) -> Optional[str]:
    """Reference solver (used by tests; the browser does this in JS)."""
    for nonce in range(limit):
        digest = hashlib.sha256(f"{token}:{nonce}".encode()).digest()
        if _leading_zero_bits(digest) >= difficulty:
            return str(nonce)
    return None


# -- pass cookie ---------------------------------------------------------

def make_pass_cookie(secret: bytes, client_ip: str, ttl: int) -> str:
    payload = json.dumps({"ip": client_ip,
                          "exp": int(time.time()) + ttl}).encode()
    return _b64(payload) + "." + _sign(secret, payload)


def check_pass_cookie(secret: bytes, value: str, client_ip: str) -> bool:
    try:
        payload_b64, sig = value.split(".", 1)
        payload = _unb64(payload_b64)
        if not sig_matches(sig, _sign(secret, payload)):
            return False
        data = json.loads(payload)
        return data["ip"] == client_ip and data["exp"] > time.time()
    except (ValueError, TypeError, KeyError, UnicodeError):
        # Fail closed. This runs on every request with a cookie, so a
        # malformed one must never raise (redteam/fuzz finding).
        return False


# -- interstitial page ---------------------------------------------------

CHALLENGE_HTML = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Checking your connection…</title>
<style>
  body {{ font-family: system-ui, sans-serif; display: grid; place-items: center;
         min-height: 100vh; margin: 0; background: #0b1020; color: #e8ecf8; }}
  .card {{ text-align: center; max-width: 26rem; padding: 2rem; }}
  .torii {{ font-size: 3rem; }}
  .bar {{ height: 4px; background: #1e2a4a; border-radius: 2px; overflow: hidden;
          margin-top: 1.5rem; }}
  .bar i {{ display: block; height: 100%; width: 30%; background: #e0483e;
           animation: slide 1s infinite alternate ease-in-out; }}
  @keyframes slide {{ to {{ transform: translateX(230%); }} }}
  small {{ color: #7d89a8; }}
</style>
<div class="card">
  <div class="torii">&#x26E9;&#xFE0F;</div>
  <h1>Verifying your connection</h1>
  <p>This site is protected by ToriiGate. Your browser will finish a quick
     check and continue automatically.</p>
  <div class="bar"><i></i></div>
  <p><small>Automated AI access requires permission from the site owner.</small></p>
</div>
<script>
(async () => {{
  const token = {token!r}, difficulty = {difficulty};
  const enc = new TextEncoder();
  const zbits = (buf) => {{
    let bits = 0;
    for (const b of new Uint8Array(buf)) {{
      if (b === 0) {{ bits += 8; continue; }}
      for (let s = 7; s >= 0; s--) {{ if ((b >> s) & 1) return bits; bits++; }}
    }}
    return bits;
  }};
  for (let nonce = 0; ; nonce++) {{
    const d = await crypto.subtle.digest("SHA-256",
        enc.encode(token + ":" + nonce));
    if (zbits(d) >= difficulty) {{
      const r = await fetch("/_torii/verify", {{
        method: "POST",
        headers: {{"content-type": "application/json"}},
        body: JSON.stringify({{token, nonce: String(nonce)}}),
      }});
      if (r.ok) location.reload();
      break;
    }}
  }}
}})();
</script>
"""


def challenge_page(token: str, difficulty: int) -> bytes:
    return CHALLENGE_HTML.format(token=token, difficulty=difficulty).encode()
