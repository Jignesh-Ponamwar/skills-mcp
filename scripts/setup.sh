#!/usr/bin/env bash
# skill-mcp — one-shot first-time setup (Linux / macOS)
# Run from the project root:  bash scripts/setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'

step()  { echo -e "\n${CYAN}[setup] $*${RESET}"; }
ok()    { echo -e "  ${GREEN}OK${RESET}  $*"; }
warn()  { echo -e "  ${YELLOW}WARN${RESET} $*"; }
fail()  { echo -e "  ${RED}FAIL${RESET} $*"; exit 1; }

# ── Step 1 — Prerequisites ────────────────────────────────────────────────────

step "Checking prerequisites ..."

PYTHON=$(command -v python3 || command -v python || echo "")
[[ -z "$PYTHON" ]] && fail "Python 3.11+ is required. Install from https://python.org"

PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    ok "Python $PY_VER"
else
    fail "Python 3.11+ required (found $PY_VER). Upgrade from https://python.org"
fi

command -v node >/dev/null 2>&1 || fail "Node.js 18+ required for wrangler. Install from https://nodejs.org"
ok "Node.js $(node --version)"

npx wrangler --version >/dev/null 2>&1 || fail "Cannot run 'npx wrangler'. Ensure Node.js is installed."
ok "wrangler available via npx"

# ── Step 2 — Initialise .env ──────────────────────────────────────────────────

step "Setting up .env ..."

if [[ ! -f .env ]]; then
    cp .env.example .env
    warn "Created .env from .env.example"
    echo ""
    echo "  Fill in the following values in .env before continuing:"
    echo "    QDRANT_URL            — Qdrant Cloud cluster URL"
    echo "    QDRANT_API_KEY        — Qdrant Cloud API key"
    echo "    WORKERS_AI_ACCOUNT_ID — Cloudflare account ID"
    echo "    WORKERS_AI_API_TOKEN  — Cloudflare API token (Workers AI Run permission)"
    echo ""
    read -r -p "  Press ENTER when you have saved .env (or Ctrl+C to abort) ..."
else
    ok ".env already exists"
fi

# ── Step 3 — Verify .env values ───────────────────────────────────────────────

step "Verifying .env values ..."

set -a; source .env; set +a

MISSING=()
[[ -z "${QDRANT_URL:-}"            ]] && MISSING+=("QDRANT_URL")
[[ -z "${QDRANT_API_KEY:-}"        ]] && MISSING+=("QDRANT_API_KEY")
[[ -z "${WORKERS_AI_ACCOUNT_ID:-}" ]] && MISSING+=("WORKERS_AI_ACCOUNT_ID")
[[ -z "${WORKERS_AI_API_TOKEN:-}"  ]] && MISSING+=("WORKERS_AI_API_TOKEN")

if [[ ${#MISSING[@]} -gt 0 ]]; then
    warn "Missing .env values: ${MISSING[*]}"
    warn "Continuing — seed/deploy may fail without them."
else
    ok "All required .env values present"
fi

# ── Step 4 — Install Python dependencies ──────────────────────────────────────

step "Installing Python dependencies ..."
$PYTHON -m pip install -r requirements.txt --quiet
ok "Python dependencies installed"

# ── Step 5 — Seed Qdrant ──────────────────────────────────────────────────────

step "Seeding Qdrant collections ..."
echo "  (Embeds skill descriptors via Cloudflare Workers AI, upserts to Qdrant)"
$PYTHON -m skill_mcp.seed.seed_skills
ok "Qdrant seeding complete"

# ── Step 6 — Deploy to Cloudflare Workers ────────────────────────────────────

step "Deploying to Cloudflare Workers ..."
npx wrangler deploy
ok "Worker deployed"

# ── Step 7 — Push secrets to Worker ──────────────────────────────────────────

step "Pushing secrets to Cloudflare Worker ..."

if [[ -n "${QDRANT_URL:-}" ]]; then
    echo "$QDRANT_URL" | npx wrangler secret put QDRANT_URL
    ok "QDRANT_URL secret set"
else
    warn "QDRANT_URL not in .env — set manually: npx wrangler secret put QDRANT_URL"
fi

if [[ -n "${QDRANT_API_KEY:-}" ]]; then
    echo "$QDRANT_API_KEY" | npx wrangler secret put QDRANT_API_KEY
    ok "QDRANT_API_KEY secret set"
else
    warn "QDRANT_API_KEY not in .env — set manually: npx wrangler secret put QDRANT_API_KEY"
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}  ✓ skill-mcp setup complete!${RESET}"
echo ""
echo -e "${CYAN}  Add this to your MCP client config:${RESET}"
echo '  { "skill-mcp": { "type": "sse", "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse" } }'
echo ""
echo -e "${CYAN}  Local server (for script execution):${RESET}"
echo '  MCP_TRANSPORT=streamable-http python3 -m skill_mcp.server'
echo ""
