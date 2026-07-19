"""Shared types for request classification and policy decisions."""

from __future__ import annotations

import ipaddress
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional


def _ip_in_cidrs(ip: str, cidrs) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for c in cidrs:
        try:
            if addr in ipaddress.ip_network(c, strict=False):
                return True
        except ValueError:
            continue
    return False


def resolve_client_ip(peer_ip: str, headers: Mapping[str, str],
                      trusted_proxies) -> str:
    """The real client IP, resistant to header spoofing.

    ``X-Forwarded-For`` / ``X-Real-IP`` are client-controllable and must
    only be believed when the connection actually arrives from a trusted
    proxy. If ``trusted_proxies`` is empty, or the socket peer is not in
    it, we trust the socket peer and ignore forwarded headers entirely
    (redteam findings C-1, F-5). When the peer *is* a trusted proxy, we
    take the right-most forwarded address that is not itself a trusted
    proxy — peeling the proxy chain the attacker cannot forge past.
    """
    if not trusted_proxies or not _ip_in_cidrs(peer_ip, trusted_proxies):
        return peer_ip or "0.0.0.0"
    xff = headers.get("x-forwarded-for", "")
    if xff:
        for hop in reversed([p.strip() for p in xff.split(",") if p.strip()]):
            if not _ip_in_cidrs(hop, trusted_proxies):
                return hop
    xreal = headers.get("x-real-ip", "").strip()
    if xreal:
        return xreal
    return peer_ip or "0.0.0.0"


class Category(str, Enum):
    """What kind of client sent the request."""

    HUMAN = "human"
    SEARCH_ENGINE = "search_engine"          # Googlebot, Bingbot, ...
    AI_TRAINING_CRAWLER = "ai_training_crawler"  # GPTBot, CCBot, Bytespider, ...
    AI_SEARCH_CRAWLER = "ai_search_crawler"      # OAI-SearchBot, PerplexityBot, ...
    AI_AGENT = "ai_agent"                    # ChatGPT-User, Claude-User, ...
    VERIFIED_AGENT = "verified_agent"        # Web Bot Auth signature verified
    SCRAPER = "scraper"                      # curl, python-requests, Scrapy, ...
    UNKNOWN_BOT = "unknown_bot"              # claims a browser but doesn't look like one
    SPOOFED_BOT = "spoofed_bot"              # claims Googlebot/GPTBot from wrong IP
    MALICIOUS = "malicious"                  # honeypot hit, probing, attack patterns


class Action(str, Enum):
    """What the gateway does with the request."""

    ALLOW = "allow"
    BLOCK = "block"            # 403 with explanation
    CHALLENGE = "challenge"    # proof-of-work interstitial (JS required)
    THROTTLE = "throttle"      # 429 + Retry-After
    TARPIT = "tarpit"          # delayed minimal response, wastes bot time
    MONETIZE = "monetize"      # 402 Payment Required (pay-per-crawl)
    LOG_ONLY = "log_only"      # record but let through (monitor mode)


@dataclass
class RequestContext:
    """Normalized view of an incoming HTTP request.

    Adapters (ASGI middleware, reverse proxy) build one of these per
    request; the whole detection pipeline works only on this type.
    """

    method: str
    path: str
    client_ip: str
    headers: Mapping[str, str]  # keys lower-cased
    query: str = ""
    ts: float = field(default_factory=time.time)

    @property
    def user_agent(self) -> str:
        return self.headers.get("user-agent", "")

    @property
    def cookies(self) -> dict:
        raw = self.headers.get("cookie", "")
        out = {}
        for part in raw.split(";"):
            if "=" in part:
                k, _, v = part.strip().partition("=")
                out[k] = v
        return out


@dataclass
class Verdict:
    """Output of the detector: what we think this client is."""

    category: Category
    score: int                  # threat score 0-100
    bot_name: Optional[str] = None
    operator: Optional[str] = None
    verified: Optional[bool] = None  # identity verified against published IP ranges
    reasons: list = field(default_factory=list)


@dataclass
class OwnResponse:
    """A response the gateway serves itself instead of the origin."""

    status: int
    headers: dict
    body: bytes


@dataclass
class Decision:
    """Final outcome for one request."""

    action: Action
    verdict: Verdict
    response: Optional[OwnResponse] = None  # None => pass through to origin
    delay_seconds: float = 0.0              # used by TARPIT

    @property
    def passed(self) -> bool:
        return self.response is None
