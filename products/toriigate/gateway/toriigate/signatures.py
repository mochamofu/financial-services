"""Signature database for known crawlers, AI agents, and probe patterns.

The signature list is the product's consumable content — in the SaaS it
is updated server-side daily and pulled by installed gateways. This file
ships a seed snapshot (verified against operator documentation as of
2026-07); ``verify_key`` links a signature to the IP range set in
:mod:`toriigate.netranges` used for anti-spoofing verification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .core import Category


@dataclass(frozen=True)
class Signature:
    pattern: str                 # lower-case substring matched against User-Agent
    name: str
    operator: str
    category: Category
    verify_key: Optional[str] = None  # key into netranges.KNOWN_RANGES, if published
    respects_robots: bool = True


SIGNATURES = [
    # --- AI training-data crawlers -------------------------------------
    Signature("gptbot", "GPTBot", "OpenAI", Category.AI_TRAINING_CRAWLER, "openai"),
    Signature("claudebot", "ClaudeBot", "Anthropic", Category.AI_TRAINING_CRAWLER),
    Signature("ccbot", "CCBot", "Common Crawl", Category.AI_TRAINING_CRAWLER),
    Signature("bytespider", "Bytespider", "ByteDance", Category.AI_TRAINING_CRAWLER,
              respects_robots=False),
    Signature("google-extended", "Google-Extended", "Google",
              Category.AI_TRAINING_CRAWLER, "googlebot"),
    Signature("applebot-extended", "Applebot-Extended", "Apple",
              Category.AI_TRAINING_CRAWLER),
    Signature("meta-externalagent", "Meta-ExternalAgent", "Meta",
              Category.AI_TRAINING_CRAWLER),
    Signature("amazonbot", "Amazonbot", "Amazon", Category.AI_TRAINING_CRAWLER),
    Signature("diffbot", "Diffbot", "Diffbot", Category.AI_TRAINING_CRAWLER),
    Signature("omgili", "Omgili", "Webz.io", Category.AI_TRAINING_CRAWLER),
    Signature("timpibot", "Timpibot", "Timpi", Category.AI_TRAINING_CRAWLER),
    Signature("pangubot", "PanguBot", "Huawei", Category.AI_TRAINING_CRAWLER),

    # --- AI search / answer-engine crawlers ----------------------------
    Signature("oai-searchbot", "OAI-SearchBot", "OpenAI",
              Category.AI_SEARCH_CRAWLER, "openai"),
    Signature("perplexitybot", "PerplexityBot", "Perplexity",
              Category.AI_SEARCH_CRAWLER, "perplexity"),
    Signature("claude-searchbot", "Claude-SearchBot", "Anthropic",
              Category.AI_SEARCH_CRAWLER),
    Signature("youbot", "YouBot", "You.com", Category.AI_SEARCH_CRAWLER),
    Signature("duckassistbot", "DuckAssistBot", "DuckDuckGo",
              Category.AI_SEARCH_CRAWLER),

    # --- On-demand AI agents (user-triggered fetch / browsing) ---------
    Signature("chatgpt-user", "ChatGPT-User", "OpenAI", Category.AI_AGENT, "openai"),
    Signature("claude-user", "Claude-User", "Anthropic", Category.AI_AGENT),
    Signature("perplexity-user", "Perplexity-User", "Perplexity",
              Category.AI_AGENT, respects_robots=False),
    Signature("mistralai-user", "MistralAI-User", "Mistral AI", Category.AI_AGENT),
    Signature("devin", "Devin", "Cognition", Category.AI_AGENT),

    # --- Traditional search engines (usually allowed) ------------------
    Signature("googlebot", "Googlebot", "Google", Category.SEARCH_ENGINE, "googlebot"),
    Signature("bingbot", "Bingbot", "Microsoft", Category.SEARCH_ENGINE, "bingbot"),
    Signature("duckduckbot", "DuckDuckBot", "DuckDuckGo", Category.SEARCH_ENGINE),
    Signature("baiduspider", "Baiduspider", "Baidu", Category.SEARCH_ENGINE),
    Signature("yandexbot", "YandexBot", "Yandex", Category.SEARCH_ENGINE),

    # --- Generic scraping tools ----------------------------------------
    Signature("python-requests", "python-requests", "unknown", Category.SCRAPER),
    Signature("python-httpx", "httpx", "unknown", Category.SCRAPER),
    Signature("aiohttp", "aiohttp", "unknown", Category.SCRAPER),
    Signature("scrapy", "Scrapy", "unknown", Category.SCRAPER),
    Signature("curl/", "curl", "unknown", Category.SCRAPER),
    Signature("wget/", "wget", "unknown", Category.SCRAPER),
    Signature("go-http-client", "Go-http-client", "unknown", Category.SCRAPER),
    Signature("node-fetch", "node-fetch", "unknown", Category.SCRAPER),
    Signature("axios/", "axios", "unknown", Category.SCRAPER),
    Signature("headlesschrome", "HeadlessChrome", "unknown", Category.SCRAPER),
    Signature("phantomjs", "PhantomJS", "unknown", Category.SCRAPER),
    Signature("selenium", "Selenium", "unknown", Category.SCRAPER),
]

# Order matters: more specific patterns must win before generic ones
# (e.g. "chatgpt-user" before a hypothetical "chatgpt"). We sort by
# pattern length descending so the longest (most specific) match wins.
_SORTED = sorted(SIGNATURES, key=lambda s: len(s.pattern), reverse=True)


def match_user_agent(user_agent: str) -> Optional[Signature]:
    ua = user_agent.lower()
    if not ua:
        return None
    for sig in _SORTED:
        if sig.pattern in ua:
            return sig
    return None


# --- Trap & probe patterns ---------------------------------------------

# Honeypot paths: listed as Disallow in the generated robots.txt and
# never linked for humans. Any client requesting them either ignores
# robots.txt or is blindly enumerating — both hostile signals.
HONEYPOT_PATHS = (
    "/.well-known/torii-trap",
    "/internal/do-not-crawl",
)

# Classic vulnerability-probing paths seen from automated attack tools.
PROBE_PATTERNS = [re.compile(p) for p in (
    r"/\.env($|\.)",
    r"/\.git(/|$)",
    r"/wp-(login|admin|config)",
    r"/phpmyadmin",
    r"/etc/passwd",
    r"\.\./",
    r"/cgi-bin/",
    r"/(config|backup|dump)\.(sql|zip|tar|gz)$",
)]

# Headers a real browser practically always sends. A "Mozilla/..." UA
# missing several of these is very likely an automation framework.
EXPECTED_BROWSER_HEADERS = ("accept", "accept-language", "accept-encoding")


def is_honeypot(path: str) -> bool:
    return any(path.startswith(h) for h in HONEYPOT_PATHS)


def matches_probe(path: str) -> bool:
    return any(p.search(path) for p in PROBE_PATTERNS)
