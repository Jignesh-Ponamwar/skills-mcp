# ── skill-mcp Dockerfile ──────────────────────────────────────────────────────
#
# Builds the local FastMCP server (Python).
# Use this when you need skills_run_script to actually execute scripts, or when
# you want to run skill-mcp without deploying to Cloudflare.
#
# The Cloudflare Worker (src/worker.py) does NOT use this Dockerfile —
# it is deployed with `wrangler deploy`.
#
# Usage (standalone):
#   docker build -t skill-mcp .
#   docker run --env-file .env -p 8000:8000 skill-mcp
#
# Usage (full stack with Qdrant — recommended):
#   docker compose up
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools for any C-extension wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (Docker layer cache optimisation)
COPY requirements.txt pyproject.toml ./

# Install all deps into a venv so we can copy it cleanly to the final image
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir fastmcp>=2.0.0 uvicorn>=0.29.0

# ── Stage 2: final image ──────────────────────────────────────────────────────
FROM python:3.11-slim AS final

# Security: run as non-root
RUN groupadd --gid 1001 skillmcp && \
    useradd --uid 1001 --gid skillmcp --no-create-home --shell /sbin/nologin skillmcp

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY --chown=skillmcp:skillmcp skill_mcp/ ./skill_mcp/
COPY --chown=skillmcp:skillmcp pyproject.toml ./

# Install the package in editable mode (no pip install needed for source)
RUN pip install --no-cache-dir --no-deps -e .

# Health check — ping the /health endpoint (served by the FastMCP server)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

USER skillmcp

# MCP server configuration via environment variables
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

# Default: HTTP transport for docker compose use
# Override CMD for stdio mode: docker run ... python -m skill_mcp.server
CMD ["python", "-X", "utf8", "-m", "skill_mcp.server"]
