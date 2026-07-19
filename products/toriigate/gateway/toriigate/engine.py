"""Gateway: ties detector, policy, challenge, and event log together.

Adapters call :meth:`Gateway.evaluate` with a :class:`RequestContext`
and either forward to the origin (``decision.passed``) or serve
``decision.response`` themselves.
"""

from __future__ import annotations

import json
import os

from . import challenge as ch
from .core import (Action, Category, Decision, OwnResponse, RequestContext,
                   Verdict)
from .events import EventLog
from .policy import Policy
from .scoring import Detector

ADMIN_PREFIX = "/_torii"

_BLOCK_BODY = """<!doctype html>
<meta charset="utf-8"><title>403 — Access denied</title>
<style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;
min-height:100vh;margin:0;background:#0b1020;color:#e8ecf8}
.card{text-align:center;max-width:28rem;padding:2rem}</style>
<div class="card"><div style="font-size:3rem">&#x26E9;&#xFE0F;</div>
<h1>Access denied</h1>
<p>Automated access to this site is controlled by the site owner.
If you operate this client and believe this is an error, contact the
site administrator.</p>
<p><small>Protected by ToriiGate</small></p></div>"""


class Gateway:
    def __init__(self, policy: Policy | None = None,
                 secret: bytes | None = None,
                 agent_registry=None):
        self.policy = policy or Policy()
        self.secret = secret or os.environ.get(
            "TORII_SECRET", "").encode() or os.urandom(32)
        self.detector = Detector(
            rate_window_seconds=self.policy.rate_limit_window)
        self.events = EventLog()
        self.agent_registry = agent_registry  # botauth.AgentRegistry | None

    # -- admin endpoints (verify / stats), shared by both adapters -------

    def handle_admin(self, ctx: RequestContext,
                     body: bytes) -> OwnResponse | None:
        """Serve /_torii/* endpoints. Returns None for unknown paths."""
        if ctx.path == f"{ADMIN_PREFIX}/verify" and ctx.method == "POST":
            try:
                data = json.loads(body or b"{}")
                ok = ch.verify_solution(self.secret, data.get("token", ""),
                                        data.get("nonce", ""), ctx.client_ip)
            except (ValueError, KeyError, TypeError):
                ok = False
            if ok:
                cookie = ch.make_pass_cookie(self.secret, ctx.client_ip,
                                             self.policy.challenge_ttl)
                return OwnResponse(200, {
                    "content-type": "application/json",
                    "set-cookie": (f"{ch.PASS_COOKIE}={cookie}; Path=/; "
                                   f"Max-Age={self.policy.challenge_ttl}; "
                                   "HttpOnly; SameSite=Lax"),
                }, b'{"ok": true}')
            return OwnResponse(400, {"content-type": "application/json"},
                               b'{"ok": false}')
        if ctx.path == f"{ADMIN_PREFIX}/stats":
            payload = json.dumps(self.events.snapshot()).encode()
            return OwnResponse(200, {"content-type": "application/json"},
                               payload)
        if ctx.path == f"{ADMIN_PREFIX}/dashboard":
            from .dashboard import dashboard_page
            return OwnResponse(200, {"content-type": "text/html; charset=utf-8"},
                               dashboard_page(self.policy.tenant))
        if ctx.path == "/robots.txt":
            from .robotsgen import generate_robots
            return OwnResponse(200, {"content-type": "text/plain"},
                               generate_robots(self.policy).encode())
        return None

    # -- main decision ---------------------------------------------------

    def evaluate(self, ctx: RequestContext) -> Decision:
        # Valid pass cookie => previously solved a challenge; let through.
        cookie = ctx.cookies.get(ch.PASS_COOKIE)
        if cookie and ch.check_pass_cookie(self.secret, cookie, ctx.client_ip):
            return self._done(ctx, Action.ALLOW, Verdict(
                Category.HUMAN, 0, reasons=["valid challenge pass"]))

        # Operator overrides come before detection.
        if self.policy.ip_blocked(ctx.client_ip):
            return self._done(ctx, Action.BLOCK, Verdict(
                Category.MALICIOUS, 100, reasons=["IP on tenant blocklist"]))
        if (self.policy.ip_allowed(ctx.client_ip)
                or self.policy.ua_allowlisted(ctx.user_agent)):
            return self._done(ctx, Action.ALLOW, Verdict(
                Category.HUMAN, 0, reasons=["tenant allowlist"]))

        # Web Bot Auth: a cryptographically verified agent identity beats
        # UA-based guessing and gets its own policy category.
        if self.agent_registry is not None and "signature" in ctx.headers:
            from . import botauth
            agent = botauth.verify_request(
                ctx.headers, ctx.headers.get("host", ""), ctx.path,
                self.agent_registry)
            if agent is not None:
                verdict = Verdict(
                    Category.VERIFIED_AGENT, 15, bot_name=agent.name,
                    operator=agent.operator, verified=True,
                    reasons=["valid Web Bot Auth signature "
                             f"(keyid={agent.keyid})"])
                action = self.policy.action_for(
                    verdict.category, verdict.score, ctx.path)
                return self._done(ctx, action, verdict)

        verdict = self.detector.classify(ctx)
        action = self.policy.action_for(verdict.category, verdict.score,
                                        ctx.path)

        # Rate limit applies on top of an ALLOW (humans hammering too).
        if action is Action.ALLOW:
            n = self.detector.rate.count(ctx.client_ip, now=ctx.ts)
            if n > self.policy.rate_limit_max:
                action = Action.THROTTLE
                verdict.reasons.append(
                    f"rate limit exceeded: {n}/{self.policy.rate_limit_max}")

        return self._done(ctx, action, verdict)

    def _done(self, ctx: RequestContext, action: Action,
              verdict: Verdict) -> Decision:
        decision = Decision(action=action, verdict=verdict,
                            response=self._response_for(action, ctx))
        if action is Action.TARPIT:
            decision.delay_seconds = self.policy.tarpit_seconds
        self.events.record(ctx, decision)
        return decision

    def _response_for(self, action: Action,
                      ctx: RequestContext) -> OwnResponse | None:
        headers = {"x-toriigate-action": action.value}
        if action in (Action.ALLOW, Action.LOG_ONLY):
            return None
        if action is Action.BLOCK:
            return OwnResponse(403, {**headers,
                                     "content-type": "text/html; charset=utf-8"},
                               _BLOCK_BODY.encode())
        if action is Action.CHALLENGE:
            token = ch.make_challenge_token(self.secret, ctx.client_ip,
                                            self.policy.challenge_difficulty)
            return OwnResponse(
                403, {**headers, "content-type": "text/html; charset=utf-8",
                      "cache-control": "no-store"},
                ch.challenge_page(token, self.policy.challenge_difficulty))
        if action is Action.THROTTLE:
            return OwnResponse(429, {**headers, "retry-after": "30",
                                     "content-type": "text/plain"},
                               b"Too many requests.\n")
        if action is Action.TARPIT:
            return OwnResponse(200, {**headers, "content-type": "text/html"},
                               b"<html><body>Loading...</body></html>")
        if action is Action.MONETIZE:
            price = self.policy.monetize_price_usd_per_1k
            return OwnResponse(402, {
                **headers, "content-type": "application/json",
                "x-toriigate-crawl-price-usd-per-1k": str(price),
            }, json.dumps({
                "error": "payment_required",
                "message": "Automated AI access to this content requires "
                           "a crawl agreement with the site owner.",
                "price_usd_per_1k_requests": price,
            }).encode())
        return None
