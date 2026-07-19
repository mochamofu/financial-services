import pathlib

from toriigate.core import Action, Category
from toriigate.policy import Policy
from toriigate.robotsgen import generate_robots

EXAMPLE = (pathlib.Path(__file__).resolve().parents[1]
           / "config" / "policy.example.yaml")


def test_defaults_block_training_allow_search():
    p = Policy()
    assert p.action_for(Category.AI_TRAINING_CRAWLER, 50, "/") == Action.BLOCK
    assert p.action_for(Category.SEARCH_ENGINE, 10, "/") == Action.ALLOW
    assert p.action_for(Category.SCRAPER, 60, "/") == Action.CHALLENGE


def test_example_yaml_loads():
    p = Policy.load(str(EXAMPLE))
    assert p.tenant == "example-corp"
    assert p.action_for(Category.AI_TRAINING_CRAWLER, 50, "/") == Action.BLOCK
    # path rule: AI agents blocked on /api/, verified agents allowed
    assert p.action_for(Category.AI_AGENT, 40, "/api/v1/x") == Action.BLOCK
    assert p.action_for(Category.VERIFIED_AGENT, 15, "/api/v1/x") == Action.ALLOW
    assert p.action_for(Category.AI_AGENT, 40, "/blog") == Action.ALLOW


def test_score_threshold_escalates_to_block():
    p = Policy()
    assert p.action_for(Category.AI_AGENT, 90, "/") == Action.BLOCK


def test_monitor_mode_only_logs():
    p = Policy.from_dict({"mode": "monitor"})
    assert p.action_for(Category.AI_TRAINING_CRAWLER, 50, "/") == Action.LOG_ONLY
    assert p.action_for(Category.HUMAN, 5, "/") == Action.ALLOW


def test_ip_lists_and_ua_allowlist():
    p = Policy.from_dict({
        "allow_ips": ["10.0.0.0/8"],
        "block_ips": ["203.0.113.7"],
        "allow_ua_substrings": ["UptimeRobot"],
    })
    assert p.ip_allowed("10.1.2.3")
    assert p.ip_blocked("203.0.113.7")
    assert not p.ip_blocked("203.0.113.8")
    assert p.ua_allowlisted("Mozilla/5.0 uptimerobot/2.0")


def test_robots_txt_lists_blocked_bots_and_traps():
    txt = generate_robots(Policy())
    assert "User-agent: GPTBot" in txt
    assert "User-agent: Bytespider" in txt
    assert "Disallow: /.well-known/torii-trap" in txt
    # allowed categories must not be disallowed
    assert "User-agent: Googlebot\n" not in txt
