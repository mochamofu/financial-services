"""Offline access-log scanner — the zero-risk "AI bot exposure" report.

A prospect points this at their existing web-server access log and gets
back: how much of their traffic is automated, which AI crawlers/agents
are hitting them, and what ToriiGate *would* have done. No deployment,
no traffic interception, and — crucially — **no protection is promised**:
it only reports what is already happening. That makes it the safe first
step (collect the real-traffic story) before selling any enforcement.

Supported formats:
- ``nginx`` / ``apache`` combined log format (default)
- ``json`` — one JSON object per line (keys: ip/remote_addr, path,
  method, user_agent/http_user_agent)

Classification is identity + trap based (User-Agent signatures, honeypot
/ probe paths). Behavioral rate signals are intentionally *not* computed
offline — they need the live gateway seeing real timing — so the report
is a conservative lower bound on what enforcement would catch.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, field

from .core import Category, RequestContext
from .policy import Policy
from .scoring import Detector

_NGINX_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[[^\]]*\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+)[^"]*" '
    r'\d+ \S+ "[^"]*" "(?P<ua>[^"]*)"')

_AI_CATEGORIES = {Category.AI_TRAINING_CRAWLER, Category.AI_SEARCH_CRAWLER,
                  Category.AI_AGENT, Category.VERIFIED_AGENT}


@dataclass
class ScanResult:
    total_lines: int = 0
    parsed: int = 0
    unparsed: int = 0
    by_category: Counter = field(default_factory=Counter)
    by_would_action: Counter = field(default_factory=Counter)
    ai_bots: Counter = field(default_factory=Counter)

    @property
    def automated(self) -> int:
        return self.parsed - self.by_category.get(Category.HUMAN.value, 0)

    @property
    def ai_requests(self) -> int:
        return sum(self.by_category.get(c.value, 0) for c in _AI_CATEGORIES)


def _parse_nginx(line: str):
    m = _NGINX_RE.match(line)
    if not m:
        return None
    d = m.groupdict()
    return d["ip"], d["method"], d["path"], d["ua"]


def _parse_json(line: str):
    try:
        o = json.loads(line)
    except ValueError:
        return None
    ua = o.get("user_agent") or o.get("http_user_agent") or o.get("ua", "")
    ip = o.get("ip") or o.get("remote_addr") or o.get("client_ip", "")
    path = o.get("path") or o.get("uri") or o.get("request_uri", "/")
    method = o.get("method") or o.get("request_method", "GET")
    if not ua and not ip:
        return None
    return ip, method, path, ua


_PARSERS = {"nginx": _parse_nginx, "apache": _parse_nginx,
            "json": _parse_json}


def scan(lines, fmt: str = "nginx", policy: Policy | None = None) -> ScanResult:
    policy = policy or Policy()
    # Logs carry no request headers, so header-completeness fingerprinting
    # would misclassify every human browser — disable it for offline scans.
    detector = Detector(header_fingerprinting=False)
    parse = _PARSERS[fmt]
    res = ScanResult()
    # Space timestamps far apart so the 10s rate window never accumulates:
    # offline scans classify by identity, not behavior (documented above).
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        res.total_lines += 1
        parsed = parse(line)
        if parsed is None:
            res.unparsed += 1
            continue
        ip, method, path, ua = parsed
        res.parsed += 1
        ctx = RequestContext(method=method, path=path, client_ip=ip or "0.0.0.0",
                             headers={"user-agent": ua}, ts=i * 100.0)
        v = detector.classify(ctx)
        action = policy.action_for(v.category, v.score, path)
        res.by_category[v.category.value] += 1
        res.by_would_action[action.value] += 1
        if v.category in _AI_CATEGORIES and v.bot_name:
            res.ai_bots[v.bot_name] += 1
    return res


def render_text(res: ScanResult) -> str:
    pct = (100 * res.automated / res.parsed) if res.parsed else 0
    ai_pct = (100 * res.ai_requests / res.parsed) if res.parsed else 0
    L = [
        "=" * 60,
        "  ⛩️  ToriiGate — AIボット露出診断レポート",
        "=" * 60,
        f"  解析行数        : {res.parsed:,}（未解析 {res.unparsed:,}）",
        f"  自動化トラフィック: {res.automated:,}  ({pct:.1f}%)",
        f"  AI関連リクエスト : {res.ai_requests:,}  ({ai_pct:.1f}%)",
        "",
        "  カテゴリ別:",
    ]
    for cat, n in res.by_category.most_common():
        L.append(f"    {cat:24s} {n:>8,}")
    L.append("")
    L.append("  ToriiGateなら何をしたか（enforce時の想定アクション）:")
    for act, n in res.by_would_action.most_common():
        L.append(f"    {act:24s} {n:>8,}")
    if res.ai_bots:
        L.append("")
        L.append("  検知したAIボット Top10:")
        for bot, n in res.ai_bots.most_common(10):
            L.append(f"    {bot:24s} {n:>8,}")
    L += ["", "  ※ 本診断は識別情報ベースの下限値です。実際の防御では挙動分析・",
          "     なりすまし検知・署名検証も加わります。防御効果を保証するもの",
          "     ではなく、現状の露出を可視化するものです。", "=" * 60]
    return "\n".join(L) + "\n"


def render_html(res: ScanResult) -> str:
    rows_cat = "".join(
        f"<tr><td>{c}</td><td>{n:,}</td></tr>"
        for c, n in res.by_category.most_common())
    rows_act = "".join(
        f"<tr><td>{a}</td><td>{n:,}</td></tr>"
        for a, n in res.by_would_action.most_common())
    rows_bot = "".join(
        f"<tr><td>{b}</td><td>{n:,}</td></tr>"
        for b, n in res.ai_bots.most_common(10)) or "<tr><td colspan=2>なし</td></tr>"
    pct = (100 * res.automated / res.parsed) if res.parsed else 0
    ai_pct = (100 * res.ai_requests / res.parsed) if res.parsed else 0
    return f"""<!doctype html><html lang="ja"><meta charset="utf-8">
<title>ToriiGate 露出診断</title>
<style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;
padding:0 1rem;color:#e8ecf8;background:#0b1020}}h1{{font-size:1.3rem}}
.tiles{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}}
.tile{{background:#131a30;border:1px solid #233052;border-radius:10px;padding:1rem;flex:1}}
.tile .n{{font-size:1.6rem;font-weight:700}}.tile .l{{color:#7d89a8;font-size:.8rem}}
table{{width:100%;border-collapse:collapse;margin:1rem 0}}
td,th{{text-align:left;padding:.4rem;border-bottom:1px solid #233052}}
small{{color:#7d89a8}}</style>
<h1>⛩️ ToriiGate — AIボット露出診断</h1>
<div class="tiles">
<div class="tile"><div class="n">{res.parsed:,}</div><div class="l">解析行数</div></div>
<div class="tile"><div class="n">{pct:.1f}%</div><div class="l">自動化トラフィック</div></div>
<div class="tile"><div class="n">{ai_pct:.1f}%</div><div class="l">AI関連</div></div>
</div>
<h2>カテゴリ別</h2><table><tr><th>分類</th><th>件数</th></tr>{rows_cat}</table>
<h2>想定アクション（enforce時）</h2><table><tr><th>アクション</th><th>件数</th></tr>{rows_act}</table>
<h2>検知したAIボット Top10</h2><table><tr><th>ボット</th><th>件数</th></tr>{rows_bot}</table>
<p><small>本診断は識別情報ベースの下限値です。防御効果の保証ではなく、現状の露出の可視化です。</small></p>
</html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="toriigate-logscan",
        description="Report AI-bot exposure from an access log (no deploy).")
    ap.add_argument("logfile", help="path to access log ('-' for stdin)")
    ap.add_argument("--format", choices=list(_PARSERS), default="nginx")
    ap.add_argument("--html", help="write an HTML report to this path")
    ap.add_argument("--json", action="store_true",
                    help="print machine-readable JSON instead of text")
    args = ap.parse_args(argv)
    import sys
    fh = sys.stdin if args.logfile == "-" else open(args.logfile, encoding="utf-8")
    try:
        res = scan(fh, fmt=args.format)
    finally:
        if fh is not sys.stdin:
            fh.close()
    if args.html:
        with open(args.html, "w", encoding="utf-8") as out:
            out.write(render_html(res))
    if args.json:
        print(json.dumps({
            "parsed": res.parsed, "unparsed": res.unparsed,
            "automated": res.automated, "ai_requests": res.ai_requests,
            "by_category": dict(res.by_category),
            "by_would_action": dict(res.by_would_action),
            "ai_bots": dict(res.ai_bots),
        }, ensure_ascii=False, indent=2))
    else:
        print(render_text(res))


if __name__ == "__main__":
    main()
