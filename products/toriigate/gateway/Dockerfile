# ToriiGate reverse-proxy — production image.
# Core runs on stdlib only; extras add YAML policies, Web Bot Auth, Redis.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY toriigate ./toriigate

# Install with the extras a production deployment uses. Drop extras you
# don't need to shrink the image.
RUN pip install --no-cache-dir ".[yaml,botauth,redis]"

# Non-root for defense in depth.
RUN useradd --uid 10001 --no-create-home torii
USER torii

EXPOSE 8080

# Liveness/readiness probe target: /_torii/healthz
# Config via env: TORII_SECRET (required in prod), TORII_REDIS_URL,
# TORII_LOG=json, TORII_ORIGIN, TORII_POLICY.
ENV TORII_ORIGIN=http://localhost:3000 \
    TORII_PORT=8080

ENTRYPOINT ["python", "-m", "toriigate.proxy"]
CMD ["--origin", "http://localhost:3000", "--port", "8080"]
