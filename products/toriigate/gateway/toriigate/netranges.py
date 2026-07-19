"""Published IP ranges of major crawler operators, for anti-spoofing.

A User-Agent header costs nothing to fake; source IP is much harder.
Operators that publish their egress ranges (Google, Microsoft, OpenAI,
Perplexity, ...) let us verify a claimed identity: "GPTBot" arriving
from an address outside OpenAI's ranges is a spoof and gets the
SPOOFED_BOT treatment regardless of policy for real GPTBot.

The CIDRs below are a *seed snapshot* — in the SaaS these are refreshed
daily from the operators' published JSON feeds (refresh URLs kept next
to each entry). ``load_ranges`` merges an updated JSON file at runtime.
Verification is only enforced for operators with a known range set;
unknown operators are never marked spoofed on IP alone.
"""

from __future__ import annotations

import ipaddress
import json
from typing import Dict, Iterable, Optional

# key -> (refresh URL, seed CIDRs)
KNOWN_RANGES: Dict[str, dict] = {
    "googlebot": {
        "refresh_url": "https://developers.google.com/static/search/apis/ipranges/googlebot.json",
        "cidrs": ["66.249.64.0/19"],
    },
    "bingbot": {
        "refresh_url": "https://www.bing.com/toolbox/bingbot.json",
        "cidrs": ["157.55.39.0/24", "207.46.13.0/24", "40.77.167.0/24"],
    },
    "openai": {
        "refresh_url": "https://openai.com/gptbot.json",
        "cidrs": ["52.230.152.0/24", "20.15.240.64/28", "20.15.240.80/28"],
    },
    "perplexity": {
        "refresh_url": "https://www.perplexity.ai/perplexitybot.json",
        "cidrs": ["107.20.236.0/24"],
    },
}

_parsed_cache: Dict[str, list] = {}


def _networks(key: str) -> list:
    if key not in _parsed_cache:
        entry = KNOWN_RANGES.get(key)
        _parsed_cache[key] = [
            ipaddress.ip_network(c) for c in (entry["cidrs"] if entry else [])
        ]
    return _parsed_cache[key]


def ip_in_ranges(ip: str, key: str) -> Optional[bool]:
    """True/False if we have ranges for *key*; None when unverifiable."""
    nets = _networks(key)
    if not nets:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in n for n in nets)


def load_ranges(path: str) -> None:
    """Merge a refreshed ranges file: ``{"openai": ["1.2.3.0/24", ...]}``."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for key, cidrs in data.items():
        KNOWN_RANGES.setdefault(key, {"refresh_url": None, "cidrs": []})
        KNOWN_RANGES[key]["cidrs"] = list(cidrs)
        _parsed_cache.pop(key, None)


def cidr_list(keys: Iterable[str]) -> list:
    out = []
    for k in keys:
        entry = KNOWN_RANGES.get(k)
        if entry:
            out.extend(entry["cidrs"])
    return out
