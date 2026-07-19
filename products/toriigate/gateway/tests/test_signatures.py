from toriigate.core import Category
from toriigate.signatures import (is_honeypot, match_user_agent,
                                  matches_probe)


def test_ai_training_crawler_ua():
    sig = match_user_agent(
        "Mozilla/5.0 AppleWebKit/537.36; compatible; "
        "GPTBot/1.2; +https://openai.com/gptbot")
    assert sig.name == "GPTBot"
    assert sig.category == Category.AI_TRAINING_CRAWLER


def test_ai_agent_ua_wins_over_generic():
    sig = match_user_agent("ChatGPT-User/2.0 (+https://openai.com/bot)")
    assert sig.name == "ChatGPT-User"
    assert sig.category == Category.AI_AGENT


def test_scraper_tools():
    assert match_user_agent("curl/8.5.0").category == Category.SCRAPER
    assert match_user_agent(
        "python-requests/2.32").category == Category.SCRAPER


def test_search_engine():
    sig = match_user_agent(
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)")
    assert sig.category == Category.SEARCH_ENGINE


def test_plain_browser_no_match():
    assert match_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36") is None


def test_honeypot_and_probe():
    assert is_honeypot("/.well-known/torii-trap")
    assert not is_honeypot("/index.html")
    assert matches_probe("/.env")
    assert matches_probe("/wp-login.php")
    assert matches_probe("/backup.sql")
    assert not matches_probe("/blog/post-1")
