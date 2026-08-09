#!/usr/bin/env python3
"""Offline demo: feed a mix of traffic through the gateway and print the
decisions, then dump dashboard stats. No network, no origin needed.

    python3 demo.py
"""

from toriigate.core import RequestContext
from toriigate.engine import Gateway
from toriigate.policy import Policy

SAMPLE_TRAFFIC = [
    ("human browser",
     {"user-agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0",
      "accept": "text/html", "accept-language": "ja", "accept-encoding": "gzip"},
     "198.51.100.10", "/products"),
    ("Googlebot (SEO — allow)",
     {"user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"},
     "66.249.66.1", "/products"),
    ("GPTBot from OpenAI range (verified training crawler)",
     {"user-agent": "GPTBot/1.2"}, "52.230.152.10", "/blog/post"),
    ("GPTBot from WRONG ip (SPOOFED — block)",
     {"user-agent": "GPTBot/1.2"}, "203.0.113.5", "/blog/post"),
    ("ClaudeBot (training crawler — block)",
     {"user-agent": "ClaudeBot/1.0"}, "203.0.113.20", "/"),
    ("ChatGPT-User agent (user-triggered — allow)",
     {"user-agent": "ChatGPT-User/2.0"}, "52.230.152.20", "/faq"),
    ("curl scraper (challenge)",
     {"user-agent": "curl/8.5.0"}, "203.0.113.30", "/api/data"),
    ("headless automation claiming a browser (challenge)",
     {"user-agent": "Mozilla/5.0 HeadlessChrome/126.0"}, "203.0.113.31", "/"),
    ("honeypot hit — ignored robots.txt (malicious)",
     {"user-agent": "Mozilla/5.0"}, "203.0.113.40",
     "/.well-known/torii-trap"),
    ("vulnerability probe (.env)",
     {"user-agent": "python-requests/2.32"}, "203.0.113.41", "/.env"),
]

ACTION_ICON = {"allow": "✅", "block": "⛔", "challenge": "\U0001f9e9",
               "throttle": "\U0001f6a6", "monetize": "\U0001f4b0",
               "tarpit": "\U0001f40c", "log_only": "\U0001f441"}


def main():
    gw = Gateway(policy=Policy(), secret=b"demo-secret")
    print("=" * 74)
    print("  ⛩️  ToriiGate — decision demo (default policy)")
    print("=" * 74)
    for label, headers, ip, path in SAMPLE_TRAFFIC:
        ctx = RequestContext(method="GET", path=path, client_ip=ip,
                             headers=headers)
        d = gw.evaluate(ctx)
        icon = ACTION_ICON.get(d.action.value, "?")
        print(f"\n{icon}  {d.action.value.upper():9s} [{d.verdict.category.value}] "
              f"score={d.verdict.score}")
        print(f"    {label}")
        print(f"    {ip}  {path}")
        if d.verdict.reasons:
            print(f"    → {d.verdict.reasons[0]}")

    print("\n" + "=" * 74)
    snap = gw.events.snapshot()
    print(f"  total requests : {snap['total_requests']}")
    print(f"  actions taken  : {snap['actions_taken']} "
          f"(blocked / challenged / throttled)")
    print(f"  by category    : {snap['by_category']}")
    print(f"  by action      : {snap['by_action']}")
    print("=" * 74)
    print("\nRun the live dashboard with:")
    print("  python3 -m toriigate.proxy --origin http://localhost:3000")
    print("  open http://localhost:8080/_torii/dashboard")


if __name__ == "__main__":
    main()
