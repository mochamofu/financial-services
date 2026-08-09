"""Prometheus text-format metrics — the observability surface ops teams
scrape. Served at ``/_torii/metrics``. Stdlib only.

Exposes request counters by category and action, a decision-latency
histogram, and build/uptime info. This is what makes the gateway
monitorable in production (alerting on block-rate spikes, latency SLOs).
"""

from __future__ import annotations

import threading
import time

from . import __version__

# Latency buckets in seconds (gateway decision overhead, not origin time).
_BUCKETS = (0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)


class Metrics:
    def __init__(self):
        self._start = time.time()
        self._lock = threading.Lock()
        self._by_cat_action: dict = {}      # (category, action) -> count
        self._lat_buckets = [0] * len(_BUCKETS)
        self._lat_inf = 0
        self._lat_sum = 0.0
        self._lat_count = 0

    def record(self, category: str, action: str) -> None:
        with self._lock:
            k = (category, action)
            self._by_cat_action[k] = self._by_cat_action.get(k, 0) + 1

    def observe_latency(self, seconds: float) -> None:
        with self._lock:
            self._lat_sum += seconds
            self._lat_count += 1
            for i, b in enumerate(_BUCKETS):
                if seconds <= b:
                    self._lat_buckets[i] += 1
                    return
            self._lat_inf += 1

    def render(self) -> bytes:
        with self._lock:
            lines = [
                "# HELP toriigate_build_info Build metadata.",
                "# TYPE toriigate_build_info gauge",
                f'toriigate_build_info{{version="{__version__}"}} 1',
                "# HELP toriigate_uptime_seconds Seconds since start.",
                "# TYPE toriigate_uptime_seconds gauge",
                f"toriigate_uptime_seconds {time.time() - self._start:.1f}",
                "# HELP toriigate_requests_total Requests by category and action.",
                "# TYPE toriigate_requests_total counter",
            ]
            for (cat, act), n in sorted(self._by_cat_action.items()):
                lines.append(
                    f'toriigate_requests_total{{category="{cat}",'
                    f'action="{act}"}} {n}')
            lines += [
                "# HELP toriigate_decision_latency_seconds Gateway decision "
                "overhead.",
                "# TYPE toriigate_decision_latency_seconds histogram",
            ]
            cumulative = 0
            for i, b in enumerate(_BUCKETS):
                cumulative += self._lat_buckets[i]
                lines.append(
                    f'toriigate_decision_latency_seconds_bucket{{le="{b}"}} '
                    f"{cumulative}")
            cumulative += self._lat_inf
            lines.append(
                'toriigate_decision_latency_seconds_bucket{le="+Inf"} '
                f"{cumulative}")
            lines.append(
                f"toriigate_decision_latency_seconds_sum {self._lat_sum:.6f}")
            lines.append(
                f"toriigate_decision_latency_seconds_count {self._lat_count}")
        return ("\n".join(lines) + "\n").encode()
