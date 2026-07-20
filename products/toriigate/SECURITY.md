# Security Policy — ToriiGate

ToriiGate sits in the request path and inspects traffic, so we hold
ourselves to a clear disclosure and handling standard.

## Reporting a vulnerability

Report suspected vulnerabilities privately — **do not open a public
issue**. Email the maintainers (security contact to be published on the
product site) with:

- affected component / version
- reproduction steps or PoC
- impact assessment

Target response: acknowledge within 3 business days, triage within 10.
We will coordinate a disclosure timeline with you and credit reporters
who wish to be named.

## Scope

In scope: the gateway (`gateway/toriigate/**`), the reverse proxy, the
ASGI middleware, challenge/signature verification, and the threat-feed
updater. Out of scope: third-party dependencies (report upstream), and
deployments the reporter does not own.

## Handling posture

- No secret material is committed to the repo. `TORII_SECRET` is supplied
  by the operator via environment.
- The gateway's own findings (blocked/challenged events) are the only
  data it records; see [docs/trust-and-compliance.md](./docs/trust-and-compliance.md)
  for exactly what is and is not stored.
- Security-relevant changes are reviewed via the red-team assessment
  process documented in [docs/security-assessment.md](./docs/security-assessment.md).

> This is a pre-GA project. This policy states intent; a staffed security
> contact and SLA are part of the go-to-market readiness work (P4 in the
> [roadmap](./docs/product-roadmap.md)).
