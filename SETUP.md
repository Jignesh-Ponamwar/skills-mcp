# Setup Guide — skill-mcp

## What you need

| Requirement | Notes |
|------------|-------|
| **Qdrant Cloud** account | Free tier — no credit card. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io) |
| **Cloudflare** account | Workers **Paid plan** ($5/month) — required for Durable Objects |
| **Python 3.11+** | For the one-time seed script and optional local server |
| **Node.js 18+** | For the `wrangler` CLI |

> Durable Objects are used to hold the FastMCP ASGI app instance in the Worker. They are not available on the Cloudflare Workers free tier.

---

## Automated setup (recommended)

A single command does everything: checks prerequisites, initialises `.env`, installs dependencies, seeds Qdrant, pushes Wrangler secrets, and deploys the Worker.

**Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

**Linux / macOS:**
```bash
bash scripts/setup.sh
```

**Cross-platform (Make):**
```bash
make setup
```

The wizard will prompt you for credentials at the right moment and explain where to find each one. Once it completes your MCP server is live — skip to [Step 4](#step-4--connect-your-mcp-client).

---

## Manual setup

### Step 1 — Get your credentials

**Qdrant Cloud:**
1. Go to [cloud.qdrant.io](https://cloud.qdrant.io) and create a cluster (~30 seconds, free tier available)
2. Click the cluster → **API Keys** → create a key
3. Copy the **cluster URL** and **API key**

**Cloudflare:**
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → right sidebar → copy your **Account ID**
2. Go to [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens) → **Create Token**
   - Use **Create Custom Token**
   - Add permissions: **Workers AI — Run** and **Workers Scripts — Edit**
   - Copy the token

---

### Step 2 — Configure and seed

```bash
git clone https://github.com/yourusername/skill-mcp
cd skill-mcp

# Install seed script dependencies
pip install -r requirements.txt

# Copy the example env file and fill in your credentials
cp .env.example .env
# Edit .env: QDRANT_URL, QDRANT_API_KEY, WORKERS_AI_ACCOUNT_ID, WORKERS_AI_API_TOKEN

# Seed all 10 bundled skills into Qdrant (idempotent — safe to re-run)
python -m skill_mcp.seed.seed_skills
# or: make seed
```

The seed script embeds skill descriptions via **Cloudflare Workers AI** (`@cf/baai/bge-small-en-v1.5`, 384-dim). The same model is used by the deployed Worker at query time, so vectors are directly comparable — no model version mismatch, no local GPU required.

Expected output:
```
[seed] Found 10 SKILL.md files
  [parsed] pdf-processing: PDF Processing
  ...
[seed] Connecting to Qdrant…
[seed] Collections ready (6 total — tiers 1, 2, and 3)

[seed] Embedding 10 skill descriptors via Cloudflare Workers AI…
  [embed] sending 10 texts to Workers AI…
  [embed] 10/10 done
[seed] Upserted 10 frontmatter points (with vectors)
[seed] Upserted 10 body points
[seed] Upserted 10 options points

[seed] Seeding tier-3 assets (references, scripts, assets)…
  ↳ reference: pdf-processing/FORMS.md
  ...
[seed] Tier-3 complete — 9 references, 6 scripts, 7 assets
[seed] Done — all six collections populated successfully
[seed] Skills loaded: pdf-processing, code-review, ...
```

---

### Step 3 — Deploy the Worker

```bash
# Install wrangler (one-time)
npm install -g wrangler

# Log in to Cloudflare
wrangler login

# Set Qdrant secrets — choose one:

# Option A: automated (reads from .env automatically)
make secrets

# Option B: manual (prompts for each value)
wrangler secret put QDRANT_URL
wrangler secret put QDRANT_API_KEY

# Deploy
wrangler deploy
# or: make deploy
```

Your MCP server is live at:
```
https://skill-mcp.<your-subdomain>.workers.dev/sse
```

---

### Step 4 — Connect your MCP client

#### Cloudflare Workers (production)

All platforms use the same SSE URL:
```
https://skill-mcp.<your-subdomain>.workers.dev/sse
```

**Claude Code** — add to `.mcp.json` or via `claude mcp add`:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

**Cursor** — add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

**Windsurf** — add to Windsurf MCP settings:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

**Cline (VSCode)** — add via Cline settings → MCP Servers:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

**Antigravity (Google)** — add to project's `.agents/mcp.json` or workspace settings:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

**GitHub Copilot** — add to `.vscode/settings.json`:
```json
{
  "github.copilot.chat.mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse"
    }
  }
}
```

#### Local development (`wrangler dev`)

```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "http://localhost:8787/sse"
    }
  }
}
```

Start the local Worker:
```bash
wrangler dev
# or via inspector: npx @modelcontextprotocol/inspector@latest sse http://localhost:8787/sse
```

---

### Step 5 — Install the master skill (optional but recommended)

The `master-skill/` directory contains ready-to-use instruction files that teach your AI agent the 3-tier skill workflow — when to call `skills_find_relevant`, how to interpret scores, and when to load Tier 3 resources.

Copy the file for your platform into your project root:

| Platform | Command |
|----------|---------|
| **Claude Code** | `cp master-skill/platforms/claude-code/CLAUDE.md ./CLAUDE.md` |
| **Cursor** | `cp master-skill/platforms/cursor/.cursorrules ./.cursorrules` |
| **Windsurf** | `cp master-skill/platforms/windsurf/.windsurfrules ./.windsurfrules` |
| **Cline** | `cp master-skill/platforms/cline/.clinerules ./.clinerules` |
| **OpenAI Codex** | `cp master-skill/platforms/codex/AGENTS.md ./AGENTS.md` |
| **GitHub Copilot** | `cp -r master-skill/platforms/copilot/.github ./.github` |
| **Aider** | `cp master-skill/platforms/aider/CONVENTIONS.md ./CONVENTIONS.md` |
| **Antigravity** | `cp -r master-skill/platforms/antigravity/.agents ./.agents` |

After copying, edit the file and replace `https://skill-mcp.<your-subdomain>.workers.dev/sse` with your actual Worker URL.

---

## Make targets reference

```bash
make help        # Show all available targets
make env         # Copy .env.example → .env (skips if .env exists)
make check       # Verify all required .env values are present
make install     # pip install -r requirements.txt
make seed        # Seed Qdrant with all skills (idempotent)
make secrets     # Auto-push QDRANT_URL + QDRANT_API_KEY from .env to Worker
make deploy      # npx wrangler deploy
make dev         # Run local FastMCP server (stdio mode)
make dev-http    # Run local FastMCP server (HTTP on :8000)
make setup       # Full first-time setup: env + install + seed + secrets + deploy
```

---

## Environment variables reference

### `.env` (used by seed script and local server)

| Variable | Required | Description |
|----------|----------|-------------|
| `QDRANT_URL` | **Yes** | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | **Yes** | Qdrant Cloud API key |
| `WORKERS_AI_ACCOUNT_ID` | **Yes** | Cloudflare account ID (for seed embeddings) |
| `WORKERS_AI_API_TOKEN` | **Yes** | Cloudflare API token with "Workers AI Run" permission |
| `FRONTMATTER_COLLECTION` | No | Override collection name (default: `skill_frontmatter`) |
| `BODY_COLLECTION` | No | Override collection name (default: `skill_body`) |
| `OPTIONS_COLLECTION` | No | Override collection name (default: `skill_options`) |
| `MCP_TRANSPORT` | No | Local server transport: `stdio` (default) or `streamable-http` |
| `MCP_HOST` | No | Local server host (default: `127.0.0.1`) |
| `MCP_PORT` | No | Local server port (default: `8000`) |

### Wrangler secrets (set via `wrangler secret put` or `make secrets`)

| Secret | Description |
|--------|-------------|
| `QDRANT_URL` | Same as `.env` — injected into the deployed Worker |
| `QDRANT_API_KEY` | Same as `.env` — injected into the deployed Worker |

The Worker's AI binding is configured in `wrangler.jsonc` via the `[ai]` block and needs no secrets — Cloudflare handles authentication automatically.

---

## Local Python server (optional)

The local FastMCP server (`skill_mcp/server.py`) is an alternative to the Cloudflare Worker, primarily useful when you need **script execution** — the Worker cannot run subprocesses in the Pyodide runtime.

```bash
pip install -e ".[local-server]"

# stdio mode (default — for Claude Code, Cursor, or any local MCP client)
python -m skill_mcp.server
# or: make dev

# HTTP mode (for remote or multi-client use)
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 python -m skill_mcp.server
# or: make dev-http
```

Local server MCP config:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "command": "python",
      "args": ["-m", "skill_mcp.server"],
      "cwd": "/path/to/skill-mcp"
    }
  }
}
```

The local server uses the same Cloudflare Workers AI REST API for embeddings as the seed script. No additional setup is needed beyond the `.env` credentials already configured.

---

## Troubleshooting

**`WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN must be set`**
→ Edit `.env` with your Cloudflare credentials. See Step 1 above.

**`Workers AI embedding failed`**
→ Your `WORKERS_AI_API_TOKEN` is missing the "Workers AI Run" permission. Recreate the token with the correct scopes.

**`qdrant_client UnexpectedResponse 401`**
→ Your `QDRANT_API_KEY` is wrong or missing in `.env`.

**`qdrant_client UnexpectedResponse 404`**
→ Collections don't exist yet. Run `python -m skill_mcp.seed.seed_skills` (or `make seed`) first.

**`[seed] ERROR: no SKILL.md files found`**
→ The seed script expects `skill_mcp/skills_data/*/SKILL.md`. Skill folders must be exactly one level deep.

**`Durable Objects not available`**
→ Durable Objects require the Cloudflare Workers Paid plan ($5/month). Upgrade at dash.cloudflare.com → Workers & Pages → Plans.

**`wrangler deploy` fails with Python Workers error**
→ Ensure `compatibility_date` in `wrangler.jsonc` is `2025-04-10` or later and `"python_workers"` is in `compatibility_flags`.

**MCP Inspector shows no tools**
→ Check the Worker logs in the Cloudflare dashboard. A startup error (e.g. a missing `QDRANT_URL` secret) will prevent tool registration. Run `make check` to verify your `.env` is complete before deploying.

**`skills_find_relevant` times out in the deployed Worker**
→ The Worker uses `js.fetch` for all outbound HTTP. If Qdrant Cloud or Workers AI is unreachable, the request will fail with a timeout. Check that your `QDRANT_URL` and `QDRANT_API_KEY` secrets are correctly set in the Worker (`wrangler secret list`), then re-run `make secrets` and `make deploy`.

**`make secrets` fails with `wrangler: command not found`**
→ Install wrangler globally first: `npm install -g wrangler`, then log in: `wrangler login`.
