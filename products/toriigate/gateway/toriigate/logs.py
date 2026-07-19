"""Structured JSON decision logging — one line per decision, ready to
ship to ELK / Datadog / CloudWatch.

Off by default; enable by setting ``TORII_LOG=json``. Kept dependency-free
(stdlib ``logging`` + ``json``) so it works anywhere the gateway runs.
"""

from __future__ import annotations

import json
import logging
import os

from .core import Decision, RequestContext

_logger = logging.getLogger("toriigate")
_enabled = os.environ.get("TORII_LOG", "").lower() == "json"

if _enabled and not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def log_decision(ctx: RequestContext, decision: Decision) -> None:
    if not _enabled:
        return
    v = decision.verdict
    _logger.info(json.dumps({
        "ts": round(ctx.ts, 3),
        "ip": ctx.client_ip,
        "method": ctx.method,
        "path": ctx.path,
        "ua": ctx.user_agent[:200],
        "category": v.category.value,
        "action": decision.action.value,
        "score": v.score,
        "bot": v.bot_name,
        "verified": v.verified,
        "reason": v.reasons[0] if v.reasons else None,
    }, ensure_ascii=False))
