"""Detector: classify a request and assign a threat score (0-100).

Signal layers, cheapest first:

1. Trap signals — honeypot paths, vulnerability probes (decisive).
2. Identity — User-Agent signature match + IP-range verification.
3. Fingerprint — browser-claiming UA missing headers browsers send.
4. Behavior — request rate for this client, repeat offenses.
"""

from __future__ import annotations

from .core import Category, RequestContext, Verdict
from .signatures import (
    EXPECTED_BROWSER_HEADERS,
    is_honeypot,
    match_user_agent,
    matches_probe,
)
from .netranges import ip_in_ranges
from .state import MemoryStore, StateStore

# Base score per category before behavioral adjustments.
_BASE_SCORES = {
    Category.HUMAN: 5,
    Category.SEARCH_ENGINE: 10,
    Category.AI_SEARCH_CRAWLER: 30,
    Category.AI_AGENT: 40,
    Category.VERIFIED_AGENT: 15,
    Category.AI_TRAINING_CRAWLER: 50,
    Category.SCRAPER: 60,
    Category.UNKNOWN_BOT: 55,
    Category.SPOOFED_BOT: 90,
    Category.MALICIOUS: 95,
}


class Detector:
    def __init__(self, rate_window_seconds: float = 10.0,
                 rate_suspicious: int = 30,
                 store: StateStore | None = None,
                 header_fingerprinting: bool = True):
        # The store holds rate windows + offender memory. Swap in a
        # RedisStore to share this state across a gateway fleet.
        self.store = store or MemoryStore(rate_window_seconds)
        self.rate_window = rate_window_seconds
        self.rate_suspicious = rate_suspicious
        # Header-completeness fingerprinting only makes sense when the
        # request's real headers are present (live gateway). Offline log
        # analysis has only UA/IP/path, so it disables this to avoid
        # flagging every header-less human browser as a bot.
        self.header_fingerprinting = header_fingerprinting

    # -- rate window (delegates to the shared store) ---------------------

    def rate_hit(self, ip: str, now: float) -> int:
        return self.store.hit(ip, now)

    def rate_count(self, ip: str, now: float) -> int:
        return self.store.count(ip, now)

    # -- repeat-offender memory ------------------------------------------

    def mark_offender(self, ip: str) -> None:
        self.store.incr_offender(ip)

    def offense_count(self, ip: str) -> int:
        return self.store.get_offender(ip)

    # -- main entry ------------------------------------------------------

    def classify(self, ctx: RequestContext) -> Verdict:
        reasons: list = []

        # 1. Trap signals are decisive regardless of claimed identity.
        if is_honeypot(ctx.path):
            self.mark_offender(ctx.client_ip)
            return Verdict(Category.MALICIOUS, 98, reasons=[
                f"honeypot path fetched: {ctx.path} (robots.txt Disallow ignored)"])
        if matches_probe(ctx.path):
            self.mark_offender(ctx.client_ip)
            return Verdict(Category.MALICIOUS, 90, reasons=[
                f"vulnerability probe pattern: {ctx.path}"])

        # 2. Identity via UA signature + IP verification.
        sig = match_user_agent(ctx.user_agent)
        category = Category.HUMAN
        bot_name = operator = None
        verified = None
        if sig is not None:
            category, bot_name, operator = sig.category, sig.name, sig.operator
            reasons.append(f"user-agent matches {sig.name} ({sig.operator})")
            if sig.verify_key:
                verified = ip_in_ranges(ctx.client_ip, sig.verify_key)
                if verified is False:
                    self.mark_offender(ctx.client_ip)
                    return Verdict(
                        Category.SPOOFED_BOT, 92, bot_name=sig.name,
                        operator=sig.operator, verified=False,
                        reasons=reasons + [
                            f"claims {sig.name} but source IP {ctx.client_ip} "
                            f"is outside {sig.operator}'s published ranges"])
                if verified:
                    reasons.append("source IP verified against published ranges")
        else:
            ua = ctx.user_agent
            if not ua:
                category = Category.SCRAPER
                reasons.append("no User-Agent header")
            elif "mozilla" in ua.lower():
                if self.header_fingerprinting:
                    missing = [h for h in EXPECTED_BROWSER_HEADERS
                               if h not in ctx.headers]
                    if len(missing) >= 2:
                        category = Category.UNKNOWN_BOT
                        reasons.append(
                            "claims a browser but lacks standard headers: "
                            + ", ".join(missing))
            else:
                # A non-empty UA that matches no known signature and is
                # not even browser-shaped (real browsers all send
                # "Mozilla/..."). Some non-browser client — treat as an
                # unknown bot rather than a human (redteam finding V-1).
                category = Category.UNKNOWN_BOT
                reasons.append(
                    f"non-browser User-Agent, no known signature: {ua[:60]!r}")

        score = _BASE_SCORES[category]

        # 3. Behavior: request rate and prior offenses.
        n = self.rate_hit(ctx.client_ip, now=ctx.ts)
        if n > self.rate_suspicious:
            score += min(25, (n - self.rate_suspicious))
            reasons.append(f"{n} requests in {self.rate_window:.0f}s window")
            if category == Category.HUMAN:
                category = Category.UNKNOWN_BOT
                score = max(score, _BASE_SCORES[Category.UNKNOWN_BOT])
        prior = self.offense_count(ctx.client_ip)
        if prior:
            score += min(20, prior * 10)
            reasons.append(f"{prior} prior offense(s) from {ctx.client_ip}")

        return Verdict(category, min(score, 100), bot_name=bot_name,
                       operator=operator, verified=verified, reasons=reasons)
