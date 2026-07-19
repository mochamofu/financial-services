"""Adversarial traffic generators — the "attacker AI" side.

Each scenario models a real evasion technique an AI scraper or agent
would use. A scenario yields (label, headers, ip, path) tuples and
declares whether a correct gateway *should* stop the traffic.

``stopped`` semantics: an action other than allow / log_only counts as
"stopped" (block, challenge, throttle, tarpit, monetize all impose a
cost on the client). We score detection = stopped / total per scenario.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterator

# Deterministic RNG so the assessment is reproducible.
RNG = random.Random(1337)

FULL_BROWSER_HEADERS = {
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "accept-language": "ja,en-US;q=0.9,en;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="126", "Google Chrome";v="126"',
    "upgrade-insecure-requests": "1",
}

CONTENT_PATHS = ["/articles/1", "/articles/2", "/products/x", "/blog/post-3",
                 "/news/today", "/docs/guide", "/pricing", "/about"]

ROTATING_UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Safari/604.1",
]


@dataclass
class Scenario:
    key: str
    title: str
    should_stop: bool           # a correct gateway stops this
    gray: bool = False          # by-design "cost not block" — informational
    note: str = ""

    def traffic(self) -> Iterator[tuple]:  # (label, headers, ip, path)
        raise NotImplementedError


def _rand_ip(prefix="203.0.113"):
    return f"{prefix}.{RNG.randint(2, 250)}"


# --- Scenarios ----------------------------------------------------------

class HonestCrawler(Scenario):
    """Baseline: a well-behaved AI training crawler that identifies itself."""
    def traffic(self):
        for p in CONTENT_PATHS:
            yield ("GPTBot honest", {"user-agent": "GPTBot/1.2"},
                   _rand_ip(), p)


class UASpoofMinimal(Scenario):
    """Claims a browser UA but sends no other browser headers."""
    def traffic(self):
        for p in CONTENT_PATHS:
            yield ("browser UA, no headers",
                   {"user-agent": FULL_BROWSER_HEADERS["user-agent"]},
                   _rand_ip(), p)


class UASpoofFullHeaders(Scenario):
    """The hard case: full browser headers, single IP, human-like paths,
    moderate rate. With no other signal this is indistinguishable from a
    human on identity alone — detection must come from behavior/volume."""
    def traffic(self):
        ip = "198.51.100.77"
        for p in CONTENT_PATHS:
            yield ("full browser mimic, 1 IP", dict(FULL_BROWSER_HEADERS),
                   ip, p)


class DistributedScrape(Scenario):
    """Full browser mimic + a fresh IP per request: defeats per-IP rate
    limiting and IP reputation. High aggregate volume, ~1 req/IP."""
    def traffic(self):
        for i in range(40):
            yield ("distributed browser mimic",
                   dict(FULL_BROWSER_HEADERS),
                   _rand_ip(f"45.{RNG.randint(1,254)}.{RNG.randint(1,254)}"),
                   RNG.choice(CONTENT_PATHS))


class RotatingUA(Scenario):
    """Cycles through many UAs, some are tool UAs, some browser-like."""
    def traffic(self):
        tool_uas = ["python-requests/2.32", "Scrapy/2.11", "curl/8.5.0",
                    "Go-http-client/2.0"]
        for i, ua in enumerate(tool_uas + ROTATING_UAS):
            yield (f"rotating UA: {ua[:24]}", {"user-agent": ua},
                   _rand_ip(), RNG.choice(CONTENT_PATHS))


class PerplexityStealth(Scenario):
    """Declared crawler first; once that would be blocked, switch to an
    undeclared browser-mimic UA and rotate source IPs (the technique
    Cloudflare attributed to Perplexity in 2025)."""
    def traffic(self):
        # phase 1: declared
        yield ("declared PerplexityBot",
               {"user-agent": "PerplexityBot/1.0"}, _rand_ip(), "/articles/1")
        # phase 2: stealth browser mimic, rotating IPs
        for p in CONTENT_PATHS:
            yield ("stealth browser mimic (post-block)",
                   dict(FULL_BROWSER_HEADERS), _rand_ip("104.28"), p)


class SlowLowScraper(Scenario):
    """Tool UA but very low rate — evades rate thresholds. The UA is the
    giveaway; a correct gateway catches it on identity, not behavior."""
    def traffic(self):
        for i, p in enumerate(CONTENT_PATHS[:5]):
            yield ("slow curl (1/min)", {"user-agent": "curl/8.5.0"},
                   "192.0.2.55", p)


class HoneypotAvoider(Scenario):
    """A careful crawler that never touches honeypot or probe paths and
    mimics a browser. Defeats the trap layer (which only catches the
    careless) — must be caught by another layer or it evades."""
    def traffic(self):
        for p in CONTENT_PATHS:
            yield ("browser mimic, avoids traps",
                   dict(FULL_BROWSER_HEADERS), "198.51.100.88", p)


class CarelessProbe(Scenario):
    """Enumerates vuln paths / hits honeypots — the careless attacker."""
    def traffic(self):
        for p in ["/.env", "/wp-login.php", "/.git/config", "/backup.sql",
                  "/.well-known/torii-trap", "/phpmyadmin"]:
            yield ("vuln probe / honeypot",
                   {"user-agent": "python-requests/2.32"}, _rand_ip(), p)


class SpoofedVerifiedBot(Scenario):
    """Claims to be GPTBot but from an IP outside OpenAI's ranges."""
    def traffic(self):
        for p in CONTENT_PATHS:
            yield ("GPTBot from wrong IP", {"user-agent": "GPTBot/1.2"},
                   _rand_ip(), p)


ATTACK_SCENARIOS = [
    HonestCrawler("honest_crawler", "正直な学習クローラー(GPTBot)", True),
    SpoofedVerifiedBot("spoofed_bot", "なりすまし(GPTBot詐称・IP不一致)", True),
    UASpoofMinimal("ua_spoof_minimal", "ブラウザUA詐称・ヘッダ欠落", True),
    RotatingUA("rotating_ua", "UAローテーション(ツール系混在)", True),
    CarelessProbe("careless_probe", "脆弱性プローブ/ハニーポット踏み", True),
    SlowLowScraper("slow_low", "低速スクレイパー(ツールUA)", True),
    PerplexityStealth("perplexity_stealth", "Perplexity型ステルス切替", True,
                      note="宣言クローラー→未宣言ブラウザ偽装＋IP切替"),
    UASpoofFullHeaders("full_mimic_1ip", "完全ブラウザ偽装(単一IP・中速)",
                       True, note="識別情報だけでは人間と区別不能。既知の難所"),
    DistributedScrape("distributed_mimic", "分散ブラウザ偽装(IP毎回変更)",
                      True, note="レート制限/IP評価を回避。既知の難所"),
    HoneypotAvoider("honeypot_avoider", "トラップ回避型(ブラウザ偽装)", True,
                    note="トラップ層は careless しか捕まえない"),
]
