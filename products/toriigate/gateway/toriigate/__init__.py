"""ToriiGate — AI access gateway.

Detects and controls AI crawlers, AI agents, and malicious automated
traffic before it reaches your website, API, or SaaS application.

Stdlib-only. Two deployment modes:

- ``toriigate.asgi.ToriiGateMiddleware`` — wrap any ASGI app
  (FastAPI / Starlette / Django ASGI / Quart).
- ``python3 -m toriigate.proxy --origin http://localhost:3000`` —
  standalone reverse proxy in front of any existing web server.
"""

__version__ = "0.1.0"

from .core import Action, Category, Decision, RequestContext  # noqa: F401
from .engine import Gateway  # noqa: F401
from .policy import Policy  # noqa: F401
