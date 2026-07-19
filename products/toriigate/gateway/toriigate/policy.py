"""Tenant policy: which categories get which action, per path.

Policies are plain dicts (loadable from YAML or JSON) so the SaaS
control plane can push them to gateways as config. See
``config/policy.example.yaml`` for the full annotated format.
"""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field
from typing import Optional

from .core import Action, Category

# Default posture: block what steals value, challenge what's ambiguous,
# never break search indexing or real users.
DEFAULT_CATEGORY_ACTIONS = {
    Category.HUMAN: Action.ALLOW,
    Category.SEARCH_ENGINE: Action.ALLOW,
    Category.AI_SEARCH_CRAWLER: Action.ALLOW,
    Category.AI_AGENT: Action.ALLOW,
    Category.VERIFIED_AGENT: Action.ALLOW,
    Category.AI_TRAINING_CRAWLER: Action.BLOCK,
    Category.SCRAPER: Action.CHALLENGE,
    Category.UNKNOWN_BOT: Action.CHALLENGE,
    Category.SPOOFED_BOT: Action.BLOCK,
    Category.MALICIOUS: Action.BLOCK,
}


@dataclass
class PathRule:
    prefix: str
    category_actions: dict = field(default_factory=dict)


@dataclass
class Policy:
    tenant: str = "default"
    mode: str = "enforce"  # "enforce" | "monitor"
    category_actions: dict = field(
        default_factory=lambda: dict(DEFAULT_CATEGORY_ACTIONS))
    path_rules: list = field(default_factory=list)
    allow_ips: list = field(default_factory=list)
    block_ips: list = field(default_factory=list)
    trusted_proxies: list = field(default_factory=list)
    allow_ua_substrings: list = field(default_factory=list)
    rate_limit_max: int = 120          # per window; above this => THROTTLE
    rate_limit_window: float = 10.0
    score_block_threshold: int = 85    # score >= this always at least BLOCK
    challenge_difficulty: int = 16     # leading zero bits of SHA-256
    #   ~2**difficulty SHA-256 tries per challenge. 16 ≈ 50-110ms of a
    #   flagged client's CPU — invisible to the rare human who is
    #   challenged, a real per-request tax on a scraper. 12 (~0.4ms) was
    #   effectively free; see redteam/ assessment.
    challenge_ttl: int = 3600          # seconds a solved challenge is valid
    tarpit_seconds: float = 8.0
    monetize_price_usd_per_1k: float = 0.0
    admin_token: str = ""              # gates /_torii/stats & /dashboard

    # -- construction ----------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "Policy":
        p = cls()
        p.tenant = data.get("tenant", p.tenant)
        p.mode = data.get("mode", p.mode)
        for cat, act in data.get("category_actions", {}).items():
            p.category_actions[Category(cat)] = Action(act)
        for rule in data.get("path_rules", []):
            p.path_rules.append(PathRule(
                prefix=rule["prefix"],
                category_actions={Category(c): Action(a)
                                  for c, a in rule.get("category_actions", {}).items()}))
        p.allow_ips = data.get("allow_ips", [])
        p.block_ips = data.get("block_ips", [])
        p.trusted_proxies = data.get("trusted_proxies", [])
        p.allow_ua_substrings = [s.lower() for s in data.get("allow_ua_substrings", [])]
        rl = data.get("rate_limit", {})
        p.rate_limit_max = rl.get("max_requests", p.rate_limit_max)
        p.rate_limit_window = rl.get("window_seconds", p.rate_limit_window)
        p.score_block_threshold = data.get("score_block_threshold",
                                           p.score_block_threshold)
        ch = data.get("challenge", {})
        p.challenge_difficulty = ch.get("difficulty", p.challenge_difficulty)
        p.challenge_ttl = ch.get("ttl_seconds", p.challenge_ttl)
        p.tarpit_seconds = data.get("tarpit_seconds", p.tarpit_seconds)
        p.monetize_price_usd_per_1k = data.get("monetize", {}).get(
            "price_usd_per_1k", p.monetize_price_usd_per_1k)
        p.admin_token = data.get("admin_token", p.admin_token)
        return p

    @classmethod
    def load(cls, path: str) -> "Policy":
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if path.endswith((".yaml", ".yml")):
            import yaml  # optional dependency; JSON policies need nothing
            return cls.from_dict(yaml.safe_load(text))
        return cls.from_dict(json.loads(text))

    # -- lookups ---------------------------------------------------------

    def ip_allowed(self, ip: str) -> bool:
        return self._ip_in(ip, self.allow_ips)

    def ip_blocked(self, ip: str) -> bool:
        return self._ip_in(ip, self.block_ips)

    @staticmethod
    def _ip_in(ip: str, cidrs: list) -> bool:
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

    def ua_allowlisted(self, user_agent: str) -> bool:
        ua = user_agent.lower()
        return any(s in ua for s in self.allow_ua_substrings)

    def action_for(self, category: Category, score: int, path: str) -> Action:
        action = self.category_actions.get(
            category, DEFAULT_CATEGORY_ACTIONS[category])
        for rule in self.path_rules:
            if path.startswith(rule.prefix) and category in rule.category_actions:
                action = rule.category_actions[category]
        if score >= self.score_block_threshold and action in (
                Action.ALLOW, Action.CHALLENGE, Action.MONETIZE):
            action = Action.BLOCK
        if self.mode == "monitor" and action is not Action.ALLOW:
            return Action.LOG_ONLY
        return action

    def blocked_ai_bot_names(self) -> list:
        """Bot names whose category the policy blocks — for robots.txt."""
        from .signatures import SIGNATURES
        out = []
        for sig in SIGNATURES:
            act = self.category_actions.get(sig.category)
            if act in (Action.BLOCK, Action.MONETIZE):
                out.append(sig.name)
        return out
