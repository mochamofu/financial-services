"""Web Bot Auth: cryptographic identity for AI agents (RFC 9421 subset).

The market is moving from "guess and block" to "verify identity, then
permit / monetize" — IETF Web Bot Auth (HTTP Message Signatures with
Ed25519 keys, draft-meunier-web-bot-auth-architecture) is the emerging
standard, backed by Cloudflare, Amazon, Akamai, and OpenAI. This module
implements a pragmatic subset:

- Agents sign requests with an Ed25519 key: ``Signature-Input`` names
  the covered components (we require ``@authority`` and ``@path``) and
  a ``keyid``/``created``/``expires``; ``Signature`` carries the bytes.
- The gateway verifies against a local *agent registry* (JSON) mapping
  keyid -> public key + operator metadata. In the SaaS the registry is
  hosted centrally and synced, giving tenants an allow/monetize list of
  verified agents.

Requires the ``cryptography`` package; without it, verification is
skipped (``verify_request`` returns ``None`` = unverifiable) so the
gateway still runs stdlib-only.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Mapping, Optional

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey)
    HAVE_ED25519 = True
except ImportError:  # pragma: no cover
    HAVE_ED25519 = False


@dataclass
class RegisteredAgent:
    keyid: str
    public_key_b64: str
    name: str
    operator: str


class AgentRegistry:
    """keyid -> registered agent. Loadable from a JSON file."""

    def __init__(self) -> None:
        self._agents: dict = {}

    def register(self, agent: RegisteredAgent) -> None:
        self._agents[agent.keyid] = agent

    def get(self, keyid: str) -> Optional[RegisteredAgent]:
        return self._agents.get(keyid)

    @classmethod
    def load(cls, path: str) -> "AgentRegistry":
        reg = cls()
        with open(path, "r", encoding="utf-8") as fh:
            for entry in json.load(fh):
                reg.register(RegisteredAgent(**entry))
        return reg


def _signature_base(authority: str, path: str, params: str) -> bytes:
    # Canonical form of the covered components, per RFC 9421 layout.
    return (f'"@authority": {authority}\n'
            f'"@path": {path}\n'
            f'"@signature-params": {params}').encode()


def _parse_sig_input(header: str) -> Optional[dict]:
    """Parse ``sig1=("@authority" "@path");keyid="...";created=...``."""
    try:
        label, _, rest = header.partition("=")
        if not rest.startswith("("):
            return None
        components_raw, _, params_raw = rest[1:].partition(")")
        components = [c.strip('"') for c in components_raw.split()]
        params = {}
        for item in params_raw.lstrip(";").split(";"):
            if not item:
                continue
            k, _, v = item.partition("=")
            params[k.strip()] = v.strip().strip('"')
        return {"label": label.strip(), "components": components,
                "params": params}
    except ValueError:
        return None


def verify_request(headers: Mapping[str, str], authority: str, path: str,
                   registry: AgentRegistry,
                   max_age: int = 300) -> Optional[RegisteredAgent]:
    """Return the registered agent if the request carries a valid
    signature; None if unsigned/invalid/unverifiable."""
    if not HAVE_ED25519:
        return None
    sig_input = headers.get("signature-input", "")
    sig_header = headers.get("signature", "")
    if not sig_input or not sig_header:
        return None
    parsed = _parse_sig_input(sig_input)
    if not parsed:
        return None
    if not {"@authority", "@path"} <= set(parsed["components"]):
        return None
    keyid = parsed["params"].get("keyid", "")
    agent = registry.get(keyid)
    if agent is None:
        return None
    created = int(parsed["params"].get("created", "0") or 0)
    if not created or abs(time.time() - created) > max_age:
        return None
    label = parsed["label"]
    prefix = f"{label}=:"
    if not (sig_header.startswith(prefix) and sig_header.endswith(":")):
        return None
    try:
        sig_bytes = base64.b64decode(sig_header[len(prefix):-1])
        pub = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(agent.public_key_b64))
        params_str = sig_input.split("=", 1)[1]
        pub.verify(sig_bytes, _signature_base(authority, path, params_str))
        return agent
    except (InvalidSignature, ValueError, TypeError):
        return None


def sign_request(private_key: "Ed25519PrivateKey", keyid: str,
                 authority: str, path: str,
                 created: int | None = None) -> dict:
    """Produce Signature-Input / Signature headers (agent side; used by
    tests and by agent operators integrating with a protected site)."""
    created = int(time.time()) if created is None else created
    params = f'("@authority" "@path");keyid="{keyid}";created={created}'
    base = _signature_base(authority, path, params)
    sig = base64.b64encode(private_key.sign(base)).decode()
    return {
        "signature-input": f"sig1={params}",
        "signature": f"sig1=:{sig}:",
    }
