"""False-positive suite — legitimate traffic that must NOT be stopped.

For a gateway, wrongly blocking Googlebot (SEO death) or real humans is
a worse business failure than missing a bot. We measure the FP rate on
the same footing as detection.
"""

from __future__ import annotations

from .attacks import FULL_BROWSER_HEADERS, CONTENT_PATHS


def _headers(ua, extra=None):
    h = dict(FULL_BROWSER_HEADERS)
    h["user-agent"] = ua
    if extra:
        h.update(extra)
    return h


class Legit:
    def __init__(self, key, title, gen):
        self.key = key
        self.title = title
        self._gen = gen

    def traffic(self):
        yield from self._gen()


def _human():
    ip = "126.10.20.30"  # a residential-looking single IP
    for p in CONTENT_PATHS:
        yield ("real human browser", dict(FULL_BROWSER_HEADERS), ip, p)


def _googlebot():
    # Real Googlebot range 66.249.64.0/19
    for p in CONTENT_PATHS[:4]:
        yield ("Googlebot (verified)",
               {"user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                              "+http://www.google.com/bot.html)"},
               "66.249.66.10", p)


def _bingbot():
    for p in CONTENT_PATHS[:3]:
        yield ("Bingbot (verified)",
               {"user-agent": "Mozilla/5.0 (compatible; bingbot/2.0)"},
               "157.55.39.20", p)


def _ai_search():
    # Answer-engine crawlers — policy allows (citation traffic).
    for ua, ip in [("OAI-SearchBot/1.0", "52.230.152.30"),
                   ("PerplexityBot/1.0", "107.20.236.10")]:
        yield (f"AI search: {ua}", {"user-agent": ua}, ip, "/pricing")


def _ai_user_agent():
    # User-triggered fetch agents — policy allows.
    for ua in ["ChatGPT-User/2.0", "Claude-User/1.0"]:
        yield (f"AI user agent: {ua}", {"user-agent": ua},
               "52.230.152.40", "/faq")


def _mobile_lean_headers():
    # A real mobile browser that sends fewer headers than desktop — must
    # not be mistaken for a bot just for leaner headers.
    h = {"user-agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like "
                        "Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"),
         "accept": "text/html,*/*;q=0.8",
         "accept-language": "ja-JP",
         "accept-encoding": "gzip, deflate"}
    for p in CONTENT_PATHS[:4]:
        yield ("real mobile browser", dict(h), "126.55.66.77", p)


LEGIT_SCENARIOS = [
    Legit("human", "本物の人間(デスクトップ)", _human),
    Legit("mobile", "本物の人間(モバイル・ヘッダ少なめ)", _mobile_lean_headers),
    Legit("googlebot", "Googlebot(正規レンジ)", _googlebot),
    Legit("bingbot", "Bingbot(正規レンジ)", _bingbot),
    Legit("ai_search", "AI検索クローラー(引用流入)", _ai_search),
    Legit("ai_user", "AIユーザーエージェント(ユーザー代理)", _ai_user_agent),
]
