#!/usr/bin/env python3
"""Fuzz harness for the attacker-reachable parsers.

Rationale: the independent audit found C-3 — a non-numeric ``created``
parameter in a Web Bot Auth signature raised an uncaught ``ValueError``,
turning a malformed header into a 500. That is a *class* of bug, not a
one-off: every parser that an unauthenticated client can reach must fail
closed (return None/False) rather than raise.

This harness feeds hostile input to each such parser and asserts the
invariant: **never raise anything outside the declared allowlist**. It is
stdlib-only and deterministic (seeded), so a failure is reproducible and
can go straight into the test suite as a regression.

    python3 -m redteam.fuzz                    # default 20k iterations
    python3 -m redteam.fuzz --iterations 200000 --seed 7
    python3 -m redteam.fuzz --target botauth   # one target only
"""

from __future__ import annotations

import argparse
import base64
import random
import string
import sys
import traceback

from toriigate import botauth, challenge as ch, logscan
from toriigate.core import RequestContext, resolve_client_ip
from toriigate.engine import Gateway
from toriigate.policy import Policy

SECRET = b"fuzz-secret"

# --- hostile input generation -------------------------------------------

_INTERESTING = [
    "", " ", "=", ".", "..", ";", "()", "(", ")", '"', '""', ":", "::",
    "sig1=", "sig1=()", 'sig1=("@method")', "a" * 4096, "\x00", "\x00\x00",
    "%s", "{}", "[]", "null", "true", "-1", "0", "1e309", "NaN", "Infinity",
    "0x41", "١٢٣", "１２３", "‮", "\ud800", "😀", "\\", "\\\\", "\r\n",
    "created=abc", "created=", "created=-1", "created=1e99", "keyid=",
    'keyid="', "expires=abc", "%00", "../", "\t", "-" * 100,
]

_ALPHABET = string.printable + "".join(chr(c) for c in range(0x80, 0x100))


def _rand_text(rng: random.Random, max_len: int = 120) -> str:
    mode = rng.randrange(6)
    if mode == 0:
        return rng.choice(_INTERESTING)
    if mode == 1:
        n = rng.randrange(0, max_len)
        return "".join(rng.choice(_ALPHABET) for _ in range(n))
    if mode == 2:  # mutate an interesting seed
        s = list(rng.choice(_INTERESTING) or "x")
        for _ in range(rng.randrange(1, 4)):
            if not s:
                break
            i = rng.randrange(len(s))
            s[i] = rng.choice(_ALPHABET)
        return "".join(s)
    if mode == 3:  # base64-ish
        raw = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40)))
        text = base64.urlsafe_b64encode(raw).decode()
        return text if rng.random() < 0.5 else text.rstrip("=")
    if mode == 4:  # dotted token shapes
        return ".".join(_rand_text(rng, 30) for _ in range(rng.randrange(1, 4)))
    return "".join(rng.choice(["a", "=", ";", '"', "(", ")", ".", ":", "1"])
                   for _ in range(rng.randrange(0, 30)))


def _rand_headers(rng: random.Random) -> dict:
    keys = ["user-agent", "accept", "accept-language", "accept-encoding",
            "cookie", "host", "signature", "signature-input",
            "x-forwarded-for", "x-real-ip", "content-length"]
    return {k: _rand_text(rng, 80)
            for k in rng.sample(keys, rng.randrange(0, len(keys) + 1))}


def _rand_path(rng: random.Random) -> str:
    if rng.random() < 0.3:
        return rng.choice(["/", "/.env", "/.well-known/torii-trap", "/api/x",
                           "/" + "a" * 3000, "//", "/%00", "/../../etc/passwd"])
    return "/" + _rand_text(rng, 40)


def _rand_ip(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return ".".join(str(rng.randrange(0, 300)) for _ in range(4))
    return _rand_text(rng, 20)


# --- targets -------------------------------------------------------------
# Each target: name -> (callable taking rng, tuple of tolerated exceptions)
# The invariant is "fails closed": a hostile input must not raise anything
# outside the allowlist. An empty allowlist means "must never raise".

def _t_parse_sig_input(rng):
    botauth._parse_sig_input(_rand_text(rng, 200))


def _make_registry():
    reg = botauth.AgentRegistry()
    if botauth.HAVE_ED25519:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PublicFormat)
        priv = Ed25519PrivateKey.generate()
        pub = base64.b64encode(priv.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)).decode()
        reg.register(botauth.RegisteredAgent("fuzz-key", pub, "Fuzz", "Fuzz"))
        # also a bogus public key, to fuzz the key-decode path
        reg.register(botauth.RegisteredAgent("bad-key", "!!!not-base64!!!",
                                             "Bad", "Bad"))
    return reg


_REGISTRY = _make_registry()


def _t_verify_request(rng):
    headers = _rand_headers(rng)
    if rng.random() < 0.6:  # bias toward reaching the signature path
        keyid = rng.choice(["fuzz-key", "bad-key", "unknown", ""])
        created = rng.choice(["abc", "", "-1", "1e99", str(2 ** 70), "0",
                              "1800000000"])
        headers["signature-input"] = (
            f'sig1=("@method" "@authority" "@path");keyid="{keyid}";'
            f'created={created}')
        headers["signature"] = rng.choice(
            [f"sig1=:{_rand_text(rng, 60)}:", _rand_text(rng, 40), "sig1=::"])
    botauth.verify_request(headers, rng.choice(["GET", "POST", ""]),
                           _rand_text(rng, 30), _rand_path(rng), _REGISTRY)


def _t_verify_solution(rng):
    ch.verify_solution(SECRET, _rand_text(rng, 150), _rand_text(rng, 20),
                       _rand_ip(rng))


def _t_check_pass_cookie(rng):
    ch.check_pass_cookie(SECRET, _rand_text(rng, 150), _rand_ip(rng))


def _t_parse_nginx(rng):
    logscan._parse_nginx(_rand_text(rng, 300))


def _t_parse_json(rng):
    if rng.random() < 0.5:
        line = rng.choice(['[1,2,3]', '"hello"', '123', 'null', 'true',
                           '{"ip": 5}', '{"ip": {"a": 1}}', '[]', '{}'])
    else:
        line = _rand_text(rng, 200)
    logscan._parse_json(line)


def _t_resolve_client_ip(rng):
    trusted = rng.choice([[], ["10.0.0.0/8"], ["not-a-cidr"],
                          ["10.0.0.0/8", "bogus"], [_rand_text(rng, 10)]])
    resolve_client_ip(_rand_ip(rng), _rand_headers(rng), trusted)


def _t_cookies(rng):
    ctx = RequestContext(method="GET", path="/", client_ip="1.2.3.4",
                         headers={"cookie": _rand_text(rng, 200)})
    _ = ctx.cookies


_GATEWAY = Gateway(policy=Policy(), secret=SECRET, agent_registry=_REGISTRY)


def _t_gateway_evaluate(rng):
    ctx = RequestContext(
        method=rng.choice(["GET", "POST", "PUT", "", _rand_text(rng, 8)]),
        path=_rand_path(rng), client_ip=_rand_ip(rng),
        headers=_rand_headers(rng))
    _GATEWAY.evaluate(ctx)


def _t_policy_from_dict(rng):
    data = {}
    if rng.random() < 0.5:
        data["category_actions"] = {_rand_text(rng, 12): _rand_text(rng, 12)}
    if rng.random() < 0.5:
        data["path_rules"] = [{"prefix": _rand_text(rng, 10)}]
    if rng.random() < 0.5:
        data["rate_limit"] = {"max_requests": _rand_text(rng, 5)}
    if rng.random() < 0.5:
        data["allow_ips"] = [_rand_text(rng, 12)]
    if rng.random() < 0.3:
        data["mode"] = _rand_text(rng, 8)
    Policy.from_dict(data)


# name -> (fn, tolerated exceptions)
TARGETS = {
    # Unauthenticated-reachable parsers: must never raise.
    "botauth_parse": (_t_parse_sig_input, ()),
    "botauth_verify": (_t_verify_request, ()),
    "challenge_solution": (_t_verify_solution, ()),
    "challenge_cookie": (_t_check_pass_cookie, ()),
    "resolve_client_ip": (_t_resolve_client_ip, ()),
    "cookies": (_t_cookies, ()),
    "gateway_evaluate": (_t_gateway_evaluate, ()),
    "logscan_nginx": (_t_parse_nginx, ()),
    "logscan_json": (_t_parse_json, ()),
    # Operator-supplied config: raising is acceptable, but only a clear,
    # typed error — never an AttributeError/IndexError from deep inside.
    "policy_from_dict": (_t_policy_from_dict, (ValueError, KeyError, TypeError)),
}


def run(target: str, iterations: int, seed: int) -> list:
    fn, tolerated = TARGETS[target]
    failures = []
    for i in range(iterations):
        rng = random.Random(f"{seed}:{target}:{i}")
        try:
            fn(rng)
        except tolerated:
            pass
        except Exception:
            failures.append({
                "target": target, "seed": seed, "iteration": i,
                "trace": traceback.format_exc(limit=6),
            })
            if len(failures) >= 5:      # enough to diagnose; stop early
                break
    return failures


def main(argv=None):
    ap = argparse.ArgumentParser(prog="redteam.fuzz")
    ap.add_argument("--iterations", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--target", choices=sorted(TARGETS), action="append")
    args = ap.parse_args(argv)

    targets = args.target or sorted(TARGETS)
    all_failures = []
    for t in targets:
        failures = run(t, args.iterations, args.seed)
        status = "FAIL" if failures else "ok"
        print(f"  [{status:4s}] {t:22s} {args.iterations:,} iterations")
        all_failures.extend(failures)

    if all_failures:
        print(f"\n{len(all_failures)} failure(s) — hostile input escaped "
              f"fail-closed handling:\n")
        for f in all_failures:
            print(f"--- {f['target']} (seed={f['seed']} iter={f['iteration']}) ---")
            print(f["trace"])
        return 1
    print("\nall targets failed closed on hostile input.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
