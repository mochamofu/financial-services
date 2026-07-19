import base64
import time

import pytest

from toriigate import botauth
from toriigate.core import Action, Category, RequestContext
from toriigate.engine import Gateway

pytestmark = pytest.mark.skipif(not botauth.HAVE_ED25519,
                                reason="cryptography not installed")


def make_agent(keyid="acme-agent-1"):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat)
    priv = Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(priv.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw)).decode()
    registry = botauth.AgentRegistry()
    registry.register(botauth.RegisteredAgent(
        keyid=keyid, public_key_b64=pub_b64,
        name="AcmeAssistant", operator="Acme AI"))
    return priv, registry


def signed_headers(priv, keyid, authority, path):
    return botauth.sign_request(priv, keyid, authority, path)


def test_valid_signature_verifies():
    priv, registry = make_agent()
    headers = {"host": "example.jp",
               **signed_headers(priv, "acme-agent-1", "example.jp", "/api/x")}
    agent = botauth.verify_request(headers, "example.jp", "/api/x", registry)
    assert agent is not None
    assert agent.name == "AcmeAssistant"


def test_path_mismatch_fails():
    priv, registry = make_agent()
    headers = signed_headers(priv, "acme-agent-1", "example.jp", "/api/x")
    assert botauth.verify_request(headers, "example.jp", "/api/other",
                                  registry) is None


def test_unknown_keyid_fails():
    priv, _ = make_agent()
    _, other_registry = make_agent(keyid="someone-else")
    headers = signed_headers(priv, "acme-agent-1", "example.jp", "/")
    assert botauth.verify_request(headers, "example.jp", "/",
                                  other_registry) is None


def test_stale_signature_fails():
    priv, registry = make_agent()
    headers = botauth.sign_request(priv, "acme-agent-1", "example.jp", "/",
                                   created=int(time.time()) - 3600)
    assert botauth.verify_request(headers, "example.jp", "/",
                                  registry) is None


def test_engine_allows_verified_agent_on_api():
    # /api/ blocks unsigned AI agents but allows verified ones — the
    # policy shape from config/policy.example.yaml.
    from toriigate.policy import Policy
    policy = Policy.from_dict({
        "category_actions": {"scraper": "block"},
        "path_rules": [{"prefix": "/api/",
                        "category_actions": {"verified_agent": "allow"}}]})
    priv, registry = make_agent()
    gw = Gateway(policy=policy, secret=b"s", agent_registry=registry)

    unsigned = RequestContext(
        method="GET", path="/api/data", client_ip="198.51.100.20",
        headers={"user-agent": "python-requests/2.32", "host": "example.jp"})
    assert gw.evaluate(unsigned).action == Action.BLOCK

    signed = RequestContext(
        method="GET", path="/api/data", client_ip="198.51.100.20",
        headers={"user-agent": "python-requests/2.32", "host": "example.jp",
                 **signed_headers(priv, "acme-agent-1", "example.jp",
                                  "/api/data")})
    d = gw.evaluate(signed)
    assert d.action == Action.ALLOW
    assert d.verdict.category == Category.VERIFIED_AGENT
    assert d.verdict.verified is True
