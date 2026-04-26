# skill-mcp — development & deployment automation
# ─────────────────────────────────────────────────────────────────────────────
# Usage:  make <target>
#
# Prerequisites: Python 3.11+, Node.js 18+ (for wrangler), pip
# Windows:  use  scripts\setup.ps1  for the interactive first-run wizard instead.
# ─────────────────────────────────────────────────────────────────────────────

# Auto-detect Python executable
ifeq ($(OS),Windows_NT)
  PYTHON   := python
  PIP      := pip
  COPY_ENV := copy .env.example .env
  SEP      := &
else
  PYTHON   := python3
  PIP      := pip3
  COPY_ENV := cp .env.example .env
  SEP      := ;
endif

.DEFAULT_GOAL := help

# ── Targets ───────────────────────────────────────────────────────────────────

.PHONY: help env check install seed deploy secrets dev dev-http setup

help:
	@echo ""
	@echo "  skill-mcp — available make targets"
	@echo "  ─────────────────────────────────────────────────────────"
	@echo "  make env        Copy .env.example → .env  (skips if .env exists)"
	@echo "  make check      Verify all required .env values are present"
	@echo "  make install    pip install -r requirements.txt"
	@echo "  make seed       Populate Qdrant with skills (requires .env)"
	@echo "  make secrets    Push QDRANT_URL + QDRANT_API_KEY to Cloudflare Worker"
	@echo "  make deploy     npx wrangler deploy"
	@echo "  make dev        Run local FastMCP server  (stdio transport)"
	@echo "  make dev-http   Run local FastMCP server  (HTTP on :8000)"
	@echo "  make setup      Full first-time setup: env → install → seed → secrets → deploy"
	@echo ""

env:
	@if [ ! -f .env ]; then $(COPY_ENV) && echo "[env] Created .env from .env.example — fill in your credentials before continuing."; else echo "[env] .env already exists — skipping."; fi

check:
	@$(PYTHON) - <<'EOF'
import os, sys
from dotenv import load_dotenv
load_dotenv()
required = {
    "QDRANT_URL":              "Qdrant Cloud cluster URL",
    "QDRANT_API_KEY":          "Qdrant Cloud API key",
    "WORKERS_AI_ACCOUNT_ID":   "Cloudflare account ID",
    "WORKERS_AI_API_TOKEN":    "Cloudflare API token (Workers AI Run permission)",
}
missing = [(k, v) for k, v in required.items() if not os.getenv(k, "").strip()]
if missing:
    print("[check] Missing required values in .env:")
    for k, desc in missing:
        print(f"  • {k}  —  {desc}")
    sys.exit(1)
print("[check] All required .env values are present.")
EOF

install:
	$(PIP) install -r requirements.txt

seed: check
	$(PYTHON) -X utf8 -m skill_mcp.seed.seed_skills

secrets:
	@echo "[secrets] Reading QDRANT_URL from .env and pushing to Worker secret ..."
	@$(PYTHON) -c "from dotenv import dotenv_values; v=dotenv_values(); print(v.get('QDRANT_URL',''))" | npx wrangler secret put QDRANT_URL
	@echo "[secrets] Reading QDRANT_API_KEY from .env and pushing to Worker secret ..."
	@$(PYTHON) -c "from dotenv import dotenv_values; v=dotenv_values(); print(v.get('QDRANT_API_KEY',''))" | npx wrangler secret put QDRANT_API_KEY
	@echo "[secrets] Done — secrets are set on the deployed Worker."

deploy:
	npx wrangler deploy

dev:
	$(PYTHON) -m skill_mcp.server

dev-http:
	MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 $(PYTHON) -m skill_mcp.server

# Full first-time setup pipeline
setup: env install seed secrets deploy
	@echo ""
	@echo "  ✓ skill-mcp is deployed and ready."
	@echo "  Worker URL: https://skill-mcp.<your-subdomain>.workers.dev"
	@echo ""
	@echo "  Add this to your MCP client config:"
	@echo '  { "skill-mcp": { "type": "sse", "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse" } }'
	@echo ""
