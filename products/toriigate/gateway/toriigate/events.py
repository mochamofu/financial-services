"""In-memory event log and aggregate counters for the dashboard.

The SaaS ships events to the control plane; this local store keeps the
gateway useful standalone and feeds the bundled dashboard.
"""

from __future__ import annotations

import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass

from .core import Decision, RequestContext


@dataclass
class Event:
    ts: float
    client_ip: str
    method: str
    path: str
    user_agent: str
    category: str
    action: str
    score: int
    bot_name: str | None
    reasons: list


class EventLog:
    def __init__(self, maxlen: int = 5000):
        self._events: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.total = 0
        self.by_category: Counter = Counter()
        self.by_action: Counter = Counter()
        self.by_bot: Counter = Counter()

    def record(self, ctx: RequestContext, decision: Decision) -> None:
        v = decision.verdict
        ev = Event(
            ts=ctx.ts, client_ip=ctx.client_ip, method=ctx.method,
            path=ctx.path, user_agent=ctx.user_agent[:200],
            category=v.category.value, action=decision.action.value,
            score=v.score, bot_name=v.bot_name, reasons=list(v.reasons),
        )
        with self._lock:
            self._events.append(ev)
            self.total += 1
            self.by_category[v.category.value] += 1
            self.by_action[decision.action.value] += 1
            if v.bot_name:
                self.by_bot[v.bot_name] += 1

    def snapshot(self, recent: int = 50) -> dict:
        with self._lock:
            events = list(self._events)[-recent:]
            protected = sum(n for a, n in self.by_action.items()
                            if a not in ("allow", "log_only"))
            return {
                "started_at": self.started_at,
                "uptime_seconds": round(time.time() - self.started_at, 1),
                "total_requests": self.total,
                "actions_taken": protected,
                "by_category": dict(self.by_category),
                "by_action": dict(self.by_action),
                "top_bots": self.by_bot.most_common(10),
                "recent_events": [asdict(e) for e in reversed(events)],
            }
