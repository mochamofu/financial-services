"""Per-tenant usage metering — the billing foundation.

The subscription model charges by *analyzed requests*. This module keeps
a monotonic, exportable tally per tenant that a billing system (Stripe
metered billing, an invoice job, a marketplace metering API) consumes.
It is deliberately separate from EventLog (recent events for the live
dashboard): metering must be monotonic and period-stamped, not a rolling
window.

Actual payment-provider wiring is out of scope here — it needs account
credentials and lives in the control plane. ``export()`` produces the
records that layer would push.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class TenantUsage:
    tenant: str
    analyzed_requests: int = 0
    by_action: dict = field(default_factory=dict)


class UsageMeter:
    def __init__(self, period: str = ""):
        # `period` is an opaque billing-period label (e.g. "2026-07"),
        # stamped by the caller — this module never reads the clock so it
        # stays deterministic and testable.
        self.period = period
        self._tenants: dict = {}
        self._lock = threading.Lock()

    def record(self, tenant: str, action: str) -> None:
        with self._lock:
            u = self._tenants.get(tenant)
            if u is None:
                u = self._tenants[tenant] = TenantUsage(tenant)
            u.analyzed_requests += 1
            u.by_action[action] = u.by_action.get(action, 0) + 1

    def usage(self, tenant: str) -> TenantUsage:
        with self._lock:
            return self._tenants.get(tenant) or TenantUsage(tenant)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "period": self.period,
                "tenants": {
                    t: {"analyzed_requests": u.analyzed_requests,
                        "by_action": dict(u.by_action)}
                    for t, u in self._tenants.items()
                },
            }

    def export(self) -> list:
        """Billing-shaped records — one per tenant — for a payment layer."""
        with self._lock:
            return [
                {"tenant": u.tenant, "period": self.period,
                 "analyzed_requests": u.analyzed_requests}
                for u in self._tenants.values()
            ]
