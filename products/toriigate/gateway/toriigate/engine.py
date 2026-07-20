"""Gateway: ties detector, policy, challenge, and event log together.

Adapters call :meth:`Gateway.evaluate` with a :class:`RequestContext`
and either forward to the origin (``decision.passed``) or serve
``decision.response`` themselves.
"""

from __future__ import annotations

import hmac
import json
import os
import warnings
from urllib.parse import parse_qs

from . import challenge as ch
from .core import (Action, Category, Decision, OwnResponse, RequestContext,
                   Verdict)
from .events import EventLog
from .logs import log_decision
from .metering import UsageMeter
from .metrics import Metrics
from .policy import Policy
from .scoring import Detector

ADMIN_PREFIX = "/_torii"


def _query_param(query: str, key: str) -> str:
    return (parse_qs(query or "").get(key) or [""])[0]

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
                 agent_registry=None, store=None):
        self.policy = policy or Policy()
        self.secret = secret or os.environ.get("TORII_SECRET", "").encode()
        if not self.secret:
            # An ephemeral per-process secret means challenge tokens and
            # pass cookies won't validate across workers/restarts, forcing
            # legitimate users into challenge loops (redteam C-9). Fine for
            # a single-process demo; warn so it's not shipped by accident.
            self.secret = os.urandom(32)
            warnings.warn(
                "TORII_SECRET is unset; using an ephemeral per-process "
                "secret. Set TORII_SECRET to a stable value in production "
                "(multi-worker deployments will break without it).",
                stacklevel=2)
        from .state import store_from_env
        self.detector = Detector(
            rate_window_seconds=self.policy.rate_limit_window,
            store=store or store_from_env(self.policy.rate_limit_window))
        self.events = EventLog()
        self.metrics = Metrics()
        self.meter = UsageMeter(period=os.environ.get("TORII_PERIOD", ""))
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
            if not self._admin_authorized(ctx):
                return self._admin_unauthorized()
            payload = json.dumps(self.events.snapshot()).encode()
            return OwnResponse(200, {"content-type": "application/json"},
                               payload)
        if ctx.path == f"{ADMIN_PREFIX}/dashboard":
            if not self._admin_authorized(ctx):
                return self._admin_unauthorized()
            from .dashboard import dashboard_page
            return OwnResponse(200, {"content-type": "text/html; charset=utf-8"},
                               dashboard_page(self.policy.tenant))
        if ctx.path == f"{ADMIN_PREFIX}/metrics":
            if not self._admin_authorized(ctx):
                return self._admin_unauthorized()
            return OwnResponse(
                200, {"content-type": "text/plain; version=0.0.4"},
                self.metrics.render())
        if ctx.path in (f"{ADMIN_PREFIX}/healthz", f"{ADMIN_PREFIX}/readyz"):
            # Liveness/readiness for load balancers and orchestrators.
            return OwnResponse(200, {"content-type": "application/json"},
                               b'{"status": "ok"}')
        if ctx.path == f"{ADMIN_PREFIX}/usage":
            if not self._admin_authorized(ctx):
                return self._admin_unauthorized()
            return OwnResponse(
                200, {"content-type": "application/json"},
                json.dumps(self.meter.snapshot()).encode())
        if ctx.path == "/robots.txt":
            from .robotsgen import generate_robots
            return OwnResponse(200, {"content-type": "text/plain"},
                               generate_robots(self.policy).encode())
        return None

    def _admin_authorized(self, ctx: RequestContext) -> bool:
        # The stats/dashboard endpoints leak traffic intelligence. When
        # an admin token is configured they require it; when it is not
        # (e.g. the local demo) they stay open (redteam C-7).
        token = self.policy.admin_token
        if not token:
            return True
        supplied = (ctx.headers.get("x-torii-admin-token", "")
                    or _query_param(ctx.query, "token"))
        return hmac.compare_digest(supplied, token)

    @staticmethod
    def _admin_unauthorized() -> OwnResponse:
        return OwnResponse(401, {"content-type": "application/json",
                                 "www-authenticate": "Bearer"},
                           b'{"error": "admin token required"}')

    # -- main decision ---------------------------------------------------

    def evaluate(self, ctx: RequestContext) -> Decision:
        # 1. Operator hard-block wins over every bypass below.
        if self.policy.ip_blocked(ctx.client_ip):
            return self._done(ctx, Action.BLOCK, Verdict(
                Category.MALICIOUS, 100, reasons=["IP on tenant blocklist"]))

        # 2. Trap paths are decisive even for a client holding a pass
        #    cookie or on the allowlist — a "verified human" fetching a
        #    honeypot or probing for vulns is still hostile (redteam C-2).
        trap = self._trap_verdict(ctx)
        if trap is not None:
            action = self.policy.action_for(trap.category, trap.score,
                                            ctx.path)
            return self._done(ctx, action, trap)

        # 3. Valid pass cookie => skip identity detection, but still
        #    subject to rate limiting (a solved challenge is not a licence
        #    to hammer — redteam C-2).
        cookie = ctx.cookies.get(ch.PASS_COOKIE)
        if cookie and ch.check_pass_cookie(self.secret, cookie, ctx.client_ip):
            return self._apply_rate(ctx, Action.ALLOW, Verdict(
                Category.HUMAN, 0, reasons=["valid challenge pass"]),
                already_hit=False)

        # 4. Tenant allowlist.
        if (self.policy.ip_allowed(ctx.client_ip)
                or self.policy.ua_allowlisted(ctx.user_agent)):
            return self._apply_rate(ctx, Action.ALLOW, Verdict(
                Category.HUMAN, 0, reasons=["tenant allowlist"]),
                already_hit=False)

        # 5. Web Bot Auth: a cryptographically verified agent identity
        #    beats UA-based guessing and gets its own policy category —
        #    but is still rate limited (redteam V-20).
        if self.agent_registry is not None and "signature" in ctx.headers:
            from . import botauth
            agent = botauth.verify_request(
                ctx.headers, ctx.method, ctx.headers.get("host", ""),
                ctx.path, self.agent_registry)
            if agent is not None:
                verdict = Verdict(
                    Category.VERIFIED_AGENT, 15, bot_name=agent.name,
                    operator=agent.operator, verified=True,
                    reasons=["valid Web Bot Auth signature "
                             f"(keyid={agent.keyid})"])
                action = self.policy.action_for(
                    verdict.category, verdict.score, ctx.path)
                return self._apply_rate(ctx, action, verdict,
                                        already_hit=False)

        # 6. Full identity + behavior detection.
        verdict = self.detector.classify(ctx)
        action = self.policy.action_for(verdict.category, verdict.score,
                                        ctx.path)
        return self._apply_rate(ctx, action, verdict, already_hit=True)

    def _trap_verdict(self, ctx: RequestContext) -> Verdict | None:
        """Honeypot / vuln-probe check, shared with the detector but run
        ahead of any allow path so traps cannot be bypassed."""
        from .signatures import is_honeypot, matches_probe
        if is_honeypot(ctx.path):
            self.detector.mark_offender(ctx.client_ip)
            return Verdict(Category.MALICIOUS, 98, reasons=[
                f"honeypot path fetched: {ctx.path} "
                "(robots.txt Disallow ignored)"])
        if matches_probe(ctx.path):
            self.detector.mark_offender(ctx.client_ip)
            return Verdict(Category.MALICIOUS, 90, reasons=[
                f"vulnerability probe pattern: {ctx.path}"])
        return None

    def _apply_rate(self, ctx: RequestContext, action: Action,
                    verdict: Verdict, already_hit: bool) -> Decision:
        # classify() already recorded a hit; other paths must record now
        # so cookie/allowlist/verified traffic counts toward the limit.
        if already_hit:
            n = self.detector.rate_count(ctx.client_ip, now=ctx.ts)
        else:
            n = self.detector.rate_hit(ctx.client_ip, now=ctx.ts)
        if action is Action.ALLOW and n > self.policy.rate_limit_max:
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
        self.metrics.record(verdict.category.value, action.value)
        self.meter.record(self.policy.tenant, action.value)
        log_decision(ctx, decision)
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
