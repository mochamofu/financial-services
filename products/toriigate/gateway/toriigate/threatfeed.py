"""Threat-intel feed updater — keeps the crawler IP-range data fresh.

The anti-spoofing check is only as good as its IP ranges: a stale seed
makes the gateway both miss spoofers *and* wrongly flag legitimate bots
whose real addresses have drifted outside the snapshot (redteam finding
F-1). This module fetches each operator's published range feed, validates
it, and writes a merged JSON that :func:`toriigate.netranges.load_ranges`
consumes — run it from cron/a sidecar daily.

Design:
- Each source has a URL and a small parser (feeds differ in shape:
  Google/OpenAI use ``{"prefixes":[{"ipv4Prefix": "..."}]}``; others
  publish a flat list).
- The HTTP fetch is injectable so the logic is testable offline and so
  operators can front it with their own mirror/proxy.
- Output is written atomically; a source that fails to fetch or yields
  zero valid CIDRs keeps its previous ranges rather than blanking them.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, List

from .netranges import KNOWN_RANGES


@dataclass
class Source:
    key: str
    url: str
    parser: Callable[[dict | list], List[str]]


def _parse_prefixes(data) -> List[str]:
    """Google/OpenAI style: {"prefixes": [{"ipv4Prefix": "1.2.3.0/24"}]}."""
    out = []
    for entry in (data or {}).get("prefixes", []):
        cidr = entry.get("ipv4Prefix") or entry.get("ipv6Prefix")
        if cidr:
            out.append(cidr)
    return out


def _parse_flat_list(data) -> List[str]:
    """Flat list style: ["1.2.3.0/24", ...] or {"cidrs": [...]}."""
    if isinstance(data, dict):
        data = data.get("cidrs") or data.get("addresses") or []
    return [str(c) for c in data]


SOURCES = [
    Source("googlebot",
           "https://developers.google.com/static/search/apis/ipranges/googlebot.json",
           _parse_prefixes),
    Source("bingbot", "https://www.bing.com/toolbox/bingbot.json",
           _parse_prefixes),
    Source("openai", "https://openai.com/gptbot.json", _parse_prefixes),
]


def _http_fetch(url: str, timeout: int = 20) -> dict | list:
    # HTTPS only, by scheme allowlist. These ranges decide who counts as a
    # *verified* crawler, so a plaintext feed could be tampered with to
    # inject an attacker's addresses into a trusted operator's range set,
    # and a file:/ URL would turn the updater into a local-file reader.
    if urllib.parse.urlsplit(url).scheme != "https":
        raise ValueError(f"refusing non-HTTPS feed URL: {url!r}")
    req = urllib.request.Request(url, headers={"user-agent": "ToriiGate-feed"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 — scheme allowlisted above
        return json.loads(resp.read())


def _valid_cidrs(cidrs) -> List[str]:
    out = []
    for c in cidrs:
        try:
            ipaddress.ip_network(c)
            out.append(c)
        except (ValueError, TypeError):
            continue
    return out


def refresh(sources=SOURCES, fetch: Callable = _http_fetch,
            previous: dict | None = None) -> dict:
    """Fetch and validate every source; return ``{key: [cidr, ...]}``.

    A source that errors or yields no valid CIDRs falls back to
    ``previous`` (or the built-in seed) so a bad refresh never blanks a
    working range set.
    """
    previous = previous or {k: v["cidrs"] for k, v in KNOWN_RANGES.items()}
    result = {}
    report = {}
    for src in sources:
        try:
            raw = fetch(src.url)
            cidrs = _valid_cidrs(src.parser(raw))
        except Exception as e:  # network / parse / anything
            cidrs, err = [], repr(e)
        else:
            err = None
        if cidrs:
            result[src.key] = cidrs
            report[src.key] = f"{len(cidrs)} cidrs"
        else:
            result[src.key] = previous.get(src.key, [])
            report[src.key] = f"KEPT PREVIOUS ({err or 'empty'})"
    result["_report"] = report
    return result


def write_atomic(path: str, data: dict) -> None:
    payload = {k: v for k, v in data.items() if not k.startswith("_")}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="toriigate-threatfeed",
        description="Refresh crawler IP-range data for anti-spoofing.")
    ap.add_argument("--out", default="ranges.json",
                    help="output JSON path (feed to netranges.load_ranges)")
    args = ap.parse_args(argv)
    data = refresh()
    write_atomic(args.out, data)
    for key, status in data["_report"].items():
        print(f"  {key}: {status}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
