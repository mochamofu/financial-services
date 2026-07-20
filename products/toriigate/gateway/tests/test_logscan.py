from toriigate import logscan
from toriigate.core import Category

NGINX_LINES = [
    # human browser
    '203.0.113.5 - - [19/Jul/2026:10:00:00 +0900] "GET /home HTTP/1.1" 200 '
    '1024 "-" "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0"',
    # Googlebot
    '66.249.66.1 - - [19/Jul/2026:10:00:01 +0900] "GET /a HTTP/1.1" 200 500 '
    '"-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"',
    # GPTBot (training crawler) from a genuine OpenAI range → verified
    '52.230.152.10 - - [19/Jul/2026:10:00:02 +0900] "GET /b HTTP/1.1" 200 500 '
    '"-" "GPTBot/1.2"',
    # curl scraper
    '203.0.113.20 - - [19/Jul/2026:10:00:03 +0900] "GET /c HTTP/1.1" 200 500 '
    '"-" "curl/8.5.0"',
    # honeypot / probe
    '203.0.113.30 - - [19/Jul/2026:10:00:04 +0900] "GET /.env HTTP/1.1" 404 '
    '0 "-" "python-requests/2.32"',
    'garbage line that will not parse',
]


def test_nginx_scan_classifies():
    res = logscan.scan(NGINX_LINES, fmt="nginx")
    assert res.parsed == 5
    assert res.unparsed == 1
    assert res.by_category[Category.HUMAN.value] == 1
    assert res.by_category[Category.SEARCH_ENGINE.value] == 1
    assert res.by_category[Category.AI_TRAINING_CRAWLER.value] == 1
    assert res.by_category[Category.MALICIOUS.value] == 1  # /.env probe
    assert res.automated == 4                              # all but the human
    assert res.ai_requests == 1                            # GPTBot
    assert res.ai_bots["GPTBot"] == 1


def test_would_actions_reflect_default_policy():
    res = logscan.scan(NGINX_LINES, fmt="nginx")
    # training crawler + probe blocked; scraper challenged; human/search allow
    assert res.by_would_action["block"] >= 2
    assert res.by_would_action["challenge"] >= 1
    assert res.by_would_action["allow"] >= 2


def test_json_format():
    lines = [
        '{"ip": "203.0.113.9", "method": "GET", "path": "/x", '
        '"user_agent": "ClaudeBot/1.0"}',
        '{"remote_addr": "126.1.2.3", "request_uri": "/y", '
        '"http_user_agent": "Mozilla/5.0 Chrome/126"}',
    ]
    res = logscan.scan(lines, fmt="json")
    assert res.parsed == 2
    assert res.by_category[Category.AI_TRAINING_CRAWLER.value] == 1


def test_render_text_and_html_nonempty():
    res = logscan.scan(NGINX_LINES, fmt="nginx")
    txt = logscan.render_text(res)
    assert "AIボット露出診断" in txt
    assert "GPTBot" in txt
    html = logscan.render_html(res)
    assert html.startswith("<!doctype html>")
    assert "GPTBot" in html
