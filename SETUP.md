# Setup Guide — skill-mcp

## What you need

| Requirement | Cost | Notes |
|------------|------|-------|
| **Qdrant Cloud** account | Free | 1 GB free cluster, no credit card. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io) |
| **Cloudflare** account | **Free** | Workers Free plan supports SQLite Durable Objects — no paid plan needed |
| **Python 3.11+** | Free | For the one-time seed script and optional local server |
| **Node.js 18+** | Free | For the `wrangler` CLI |

> **Everything is free.** skill-mcp uses SQLite-backed Durable Objects (`new_sqlite_classes` in `wrangler.jsonc`), which are fully supported on the Cloudflare Workers **Free** plan. The free tier allows 100,000 requests/day — more than enough for personal and team use. You only need the $5/month Workers Paid plan if you exceed that limit.
>
> **Prefer Docker?** Skip Cloudflare entirely and run locally — see [Option C: Docker](#option-c--docker-fully-local).

---

## Option A — Automated setup (Cloudflare, recommended)

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

## Option C — Docker (fully local)

No Cloudflare account required. Runs Qdrant in a container alongside the MCP server. Useful for local-only use, air-gapped environments, or testing before deploying to Cloudflare.

**Prerequisites:** Docker Desktop or Docker Engine + Compose plugin, and `.env` with just `WORKERS_AI_ACCOUNT_ID` + `WORKERS_AI_API_TOKEN` (needed for embedding generation).

```bash
# Copy env template and fill in Cloudflare credentials only
cp .env.example .env
# Edit .env: set WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN
# QDRANT_URL and QDRANT_API_KEY are not needed — Qdrant runs locally

# Start everything: Qdrant → seed → MCP server
docker compose up

# Or in background
docker compose up -d
docker compose logs -f server
```

Your MCP server is live at `http://localhost:8000/sse`.

After adding or updating skills:
```bash
docker compose run --rm seed
# or: make docker-seed
```

To stop (Qdrant data is preserved in a named volume):
```bash
docker compose down
# Full reset including data: docker compose down -v
```

MCP client config for Docker mode:
```json
{
  "mcpServers": {
    "skill-mcp": {
      "transport": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Option B — Manual setup (Cloudflare)

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

# Seed all 30 bundled skills into Qdrant (idempotent — safe to re-run)
python -X utf8 -m skill_mcp.seed.seed_skills
# or: make seed
```

The seed script runs a **prompt-injection scan** on every skill before ingesting it. Blocked skills are skipped with a clear error. Then it embeds skill descriptions via **Cloudflare Workers AI** (`@cf/baai/bge-small-en-v1.5`, 384-dim) — the same model the deployed Worker uses at query time. Vectors are always directly comparable. No local GPU required.

Expected output:
```
[seed] Found 30 SKILL.md files
  [parsed] api-integration: API Integration
  [parsed] claude-api: Claude API
  ...
[seed] Connecting to Qdrant…
[seed] Collections ready (6 total — tiers 1, 2, and 3)

[seed] Embedding 30 skill descriptors via Cloudflare Workers AI…
  [embed] sending 30 texts to Workers AI…
  [embed] 30/30 done
[seed] Upserted 30 frontmatter points (with vectors)
[seed] Upserted 30 body points
[seed] Upserted 30 options points

[seed] Seeding tier-3 assets (references, scripts, assets)…
  ↳ reference: pdf-processing/FORMS.md
  ...
[seed] Tier-3 complete — 12 references, 8 scripts, 9 assets
[seed] Done — all six collections populated successfully
[seed] Skills loaded: api-integration, claude-api, ...
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
make seed        # Seed Qdrant with all skills — runs injection scan first (idempotent)
make secrets     # Auto-push QDRANT_URL + QDRANT_API_KEY from .env to Worker
make deploy      # npx wrangler deploy
make dev         # Run local FastMCP server (stdio mode)
make dev-http    # Run local FastMCP server (HTTP on :8000)
make setup       # Full first-time setup: env + install + seed + secrets + deploy
make validate    # Validate all SKILL.md files — schema + prompt-injection scan
make docker-up   # Start Qdrant + seed + MCP server via Docker Compose
make docker-down # Stop Docker stack (data preserved)
make docker-seed # Re-seed Qdrant in the running Docker stack
```

---

## Environment variables reference

### `.env` (used by seed script and local server)

| Variable | Cloudflare deploy | Docker local | Description |
|----------|:-----------------:|:------------:|-------------|
| `QDRANT_URL` | **Required** | Not needed | Qdrant Cloud cluster URL (Docker uses its own local Qdrant) |
| `QDRANT_API_KEY` | **Required** | Not needed | Qdrant Cloud API key |
| `WORKERS_AI_ACCOUNT_ID` | **Required** | **Required** | Cloudflare account ID (for embedding generation) |
| `WORKERS_AI_API_TOKEN` | **Required** | **Required** | Cloudflare API token with "Workers AI Run" permission |
| `FRONTMATTER_COLLECTION` | No | No | Override collection name (default: `skill_frontmatter`) |
| `BODY_COLLECTION` | No | No | Override collection name (default: `skill_body`) |
| `OPTIONS_COLLECTION` | No | No | Override collection name (default: `skill_options`) |
| `MCP_TRANSPORT` | No | No | Local server transport: `stdio` (default) or `streamable-http` |
| `MCP_HOST` | No | No | Local server host (default: `127.0.0.1`) |
| `MCP_PORT` | No | No | Local server port (default: `8000`) |

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

## Validating skills

Before seeding or submitting a PR, validate your SKILL.md files locally:

```bash
# Validate all skills (schema + prompt-injection scan)
python scripts/validate_skills.py

# Validate a single skill
python scripts/validate_skills.py skill_mcp/skills_data/my-skill/SKILL.md

# Run the injection scanner directly on a file
python -m skill_mcp.security.prompt_injection skill_mcp/skills_data/my-skill/SKILL.md

# Make shortcut
make validate
```

The validator checks:
- YAML frontmatter parses without errors
- Required fields present: `name`, `description`, `license`, `metadata.triggers`
- `name` matches the directory slug
- Triggers are natural-language strings, ≤120 chars each
- License is a recognised SPDX identifier
- Body is non-empty
- Tier-3 file references in the body exist on disk
- 9 categories of prompt-injection patterns (CRITICAL/HIGH = blocked, MEDIUM/LOW = warned)

The seed script runs the same scan automatically. Skills that fail with CRITICAL or HIGH findings are skipped — they will not be written to Qdrant.

---

## Troubleshooting

**`WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN must be set`**
→ Edit `.env` with your Cloudflare credentials. See Step 1 above.

**`Workers AI embedding failed`**
→ Your `WORKERS_AI_API_TOKEN` is missing the "Workers AI Run" permission. Recreate the token with the correct scopes.

**`qdrant_client UnexpectedResponse 401`**
→ Your `QDRANT_API_KEY` is wrong or missing in `.env`.

**`qdrant_client UnexpectedResponse 404`**
→ Collections don't exist yet. Run `python -X utf8 -m skill_mcp.seed.seed_skills` (or `make seed`) first.

**`[seed] ERROR: no SKILL.md files found`**
→ The seed script expects `skill_mcp/skills_data/*/SKILL.md`. Skill folders must be exactly one level deep.

**`[seed] BLOCKED: prompt-injection scan failed`**
→ A skill file contains content that triggered the injection scanner. Review the finding details printed above the error. If it's a false positive (e.g., legitimate code containing flagged patterns), open an issue — do not disable the scanner.

**`Durable Objects not available` / `Durable Objects require a paid plan`**
→ skill-mcp uses SQLite-backed Durable Objects (`new_sqlite_classes` in `wrangler.jsonc`), which are available on the **free** Workers plan. If you see this error, ensure `wrangler.jsonc` contains `"new_sqlite_classes"` in the migrations block (not `"new_classes"` which is KV-backed and paid-only).

**`wrangler deploy` fails with Python Workers error**
→ Ensure `compatibility_date` in `wrangler.jsonc` is `2025-04-10` or later and `"python_workers"` is in `compatibility_flags`.

**MCP Inspector shows no tools**
→ Check the Worker logs in the Cloudflare dashboard. A startup error (e.g. a missing `QDRANT_URL` secret) will prevent tool registration. Run `make check` to verify your `.env` is complete before deploying.

**`skills_find_relevant` times out in the deployed Worker**
→ The Worker uses `js.fetch` for all outbound HTTP. If Qdrant Cloud or Workers AI is unreachable, the request will fail with a timeout. Check that your `QDRANT_URL` and `QDRANT_API_KEY` secrets are correctly set in the Worker (`wrangler secret list`), then re-run `make secrets` and `make deploy`.

**`make secrets` fails with `wrangler: command not found`**
→ Install wrangler globally first: `npm install -g wrangler`, then log in: `wrangler login`.
