# skill-mcp

<div align="center">

![Skills-MCP Logo](./Skills-MCP%20Minimal%20Logo.png)

**A self-hostable, open-source Skills registry for AI agents — delivered over MCP.**  
Semantic discovery · Progressive disclosure · 30 production-ready skills · Runs on Cloudflare Workers

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-F38020.svg)](https://workers.cloudflare.com)
[![Skills](https://img.shields.io/badge/bundled%20skills-30-brightgreen.svg)](skill_mcp/skills_data/)

</div>

---

## The Problem

AI agents are great at *knowing things* but often inconsistent at *doing specific tasks well*.

Ask Claude or GPT to "write a Stripe integration" and you get something functional — but maybe it doesn't verify webhook signatures, uses a deprecated API, or misses idempotency keys. Ask it to "containerize this app" and it might skip non-root users, ignore layer caching, or forget `.dockerignore`.

**The knowledge is there. The reliable procedural workflow isn't.**

The deeper problem: every time you start a new chat, a new project, or switch tools, the agent starts from scratch. There's no shared, versioned, searchable library of *how to do X correctly* that agents can pull from on demand.

## The Solution — skill-mcp

**skill-mcp** is a self-hostable registry of Skills — expert step-by-step procedures, domain heuristics, output formats, and bundled reference material — that AI agents discover and load at the moment they need them, over MCP.

```
You:   "Set up Stripe subscriptions with webhooks"

Agent: → skills_find_relevant("set up Stripe subscriptions webhooks")
         Score 0.89 → stripe-integration

       → skills_get_body("stripe-integration")
         Loads: which API to use, webhook verification pattern,
                idempotency keys, security checklist, go-live steps

       → Executes task correctly, first time, every time
```

The agent doesn't guess. It retrieves authoritative, versioned instructions — the same way a senior engineer would consult a runbook.

---

## What Makes It Different

| | skill-mcp | System prompt stuffing | Per-project CLAUDE.md | Prompt libraries |
|---|---|---|---|---|
| **Searchable** | ✅ Semantic search across 30+ skills | ❌ Everything loaded always | ❌ Static per project | ❌ Manual lookup |
| **On-demand** | ✅ Load only what's needed | ❌ Burns context window | ❌ Burns context window | ❌ Copy-paste |
| **Versioned** | ✅ Seed once, update centrally | ❌ Must update every file | ❌ Must update every project | ❌ No source of truth |
| **Bundled assets** | ✅ References, scripts, templates | ❌ | ❌ | ❌ |
| **Self-hostable** | ✅ Your infra, your data | ❌ | ✅ | ✅ |
| **8 AI platforms** | ✅ Claude Code, Cursor, Windsurf... | varies | varies | varies |

---

## How It Works in 60 Seconds

### 1. Skills are stored in Qdrant with semantic vectors

Each skill is a `SKILL.md` file with YAML frontmatter. Only the description and trigger phrases (~100 tokens) are embedded — keeping the search space semantically clean. The full instructions stay in payload-only collections and are fetched on demand.

### 2. Agents discover skills with natural language

```
skills_find_relevant("write pytest tests for a FastAPI endpoint")
→ test-writer (score: 0.84)
→ fastapi     (score: 0.71)
```

Score thresholds: **> 0.6** strong match · **0.4–0.6** review description · **< 0.4** no match

### 3. Progressive disclosure — load only what you need

```
Tier 1 — Discovery   skills_find_relevant()         ← always call first
Tier 2 — Load        skills_get_body()              ← full instructions + manifest
Tier 2 — Options     skills_get_options()           ← config, variants (optional)
Tier 3 — Supplement  skills_get_reference()         ← only if instructions reference it
                     skills_run_script()            ← only if instructions reference it
                     skills_get_asset()             ← only if instructions reference it
```

Nothing is loaded speculatively. The agent reads `tier3_manifest` (a list of available files returned with the body) and fetches only what the instructions explicitly reference.

### 4. The server runs as a single Cloudflare Python Worker

No separate backend. No database server to manage. No GPU. Cloudflare Workers AI handles embeddings at query time using the same model the seed script uses — vectors are always comparable.

---

## Architecture

### Six Qdrant collections — one purpose each

| Collection | Vector | Contents |
|-----------|--------|----------|
| `skill_frontmatter` | ✅ 384-dim | Name, description, tags, trigger phrases — the discovery layer |
| `skill_body` | payload only | Full markdown instructions + system prompt addition |
| `skill_options` | payload only | Config schema, variants, dependencies, limitations |
| `skill_references` | payload only | Markdown reference docs bundled with the skill |
| `skill_scripts` | payload only | Executable scripts (source stored server-side; never sent to agents) |
| `skill_assets` | payload only | Templates and static output format resources |

### Six MCP tools — 3-tier progressive disclosure

| Tier | Tool | When to call |
|------|------|-------------|
| 1 | `skills_find_relevant(query, top_k)` | **Always first** — semantic search, returns ranked skills with scores |
| 2 | `skills_get_body(skill_id)` | After finding a match — full instructions + `tier3_manifest` |
| 2 | `skills_get_options(skill_id)` | Optional — config schema, variants, dependencies, limitations |
| 3 | `skills_get_reference(skill_id, filename)` | Only when instructions reference a specific doc |
| 3 | `skills_run_script(skill_id, filename, input_data)` | Only when instructions direct script execution |
| 3 | `skills_get_asset(skill_id, filename)` | Only when instructions reference a specific template |

### Why embed only the frontmatter?

Embedding the full SKILL.md as a single vector pollutes the search space with instruction prose — text that was never meant to be searched. skill-mcp embeds only `description + trigger_phrases` (~100 tokens), keeping the vector space semantically clean and search results relevant.

### Embeddings — no model version drift

The Worker uses **Cloudflare Workers AI** (`@cf/baai/bge-small-en-v1.5`, 384-dim) for query-time embedding. The seed script calls the same model via the REST API. Seed-time and query-time vectors are directly comparable — no local GPU, no embedding server, no drift.

---

## Bundled Skills (30)

Production-ready skills sourced from official repositories (Anthropic, Google Gemini, Vercel, Cloudflare, Stripe) and community engineering best practices.

### 🔧 Core Development
| Skill | What it does |
|-------|-------------|
| `api-integration` | REST/GraphQL clients with auth, pagination, retries, error handling, and OpenAPI alignment |
| `code-review` | Structured security + quality review with CRITICAL/HIGH/MEDIUM/LOW severity ratings and fix snippets |
| `data-analysis` | EDA, cleaning, statistics, visualizations, and actionable insights from CSV/tabular data |
| `git-commit-writer` | Conventional Commits from diffs — type, scope, breaking changes, and co-authors |
| `readme-writer` | Professional README.md with badges, usage, API docs, and contributing guide |
| `sql-query-writer` | Optimized SQL — window functions, CTEs, indexes, explain plans, and common anti-patterns |
| `test-writer` | pytest, Jest, and Go test suites with full edge case coverage and mocking patterns |
| `web-scraper` | Structured data extraction with rate limiting, pagination, and anti-bot handling |

### 📄 Documents and Office
| Skill | What it does |
|-------|-------------|
| `docx-creator` | Create and edit Word documents with python-docx — tables, styles, headers, tracked changes |
| `pdf-processing` | Extract text/tables, fill forms, merge/split PDFs — full Tier 3 scripts and references |
| `pptx-creator` | Build PowerPoint presentations with pptxgenjs — charts, images, design principles |
| `xlsx-creator` | Excel spreadsheets with openpyxl — formulas, formatting, charts, financial model conventions |

### 🤖 AI and LLM Platforms
| Skill | What it does |
|-------|-------------|
| `claude-api` | Anthropic SDK: tool use, streaming, vision, prompt caching, extended thinking, batch |
| `gemini-api` | Google Gemini API: multimodal, function calling, structured output, current models/SDKs |
| `openai-api` | OpenAI: GPT-4o, tool use, structured output, DALL-E, Whisper, TTS, batch processing |
| `llm-prompt-engineering` | Chain-of-thought, few-shot, structured output, agent system prompt design, anti-patterns |
| `mcp-server-builder` | Build MCP servers with FastMCP (Python) or TypeScript SDK — tools, resources, prompts |

### ☁️ Cloud Platforms and Infrastructure
| Skill | What it does |
|-------|-------------|
| `cloudflare-workers` | Workers, Pages, KV, D1, R2, Workers AI, Vectorize, Durable Objects, Wrangler |
| `docker-containerization` | Production Dockerfiles, multi-stage builds, Docker Compose, security hardening |
| `github-actions` | CI/CD workflows, matrix builds, caching, Docker publishing, release automation |
| `terraform` | IaC for AWS/GCP/Azure — modules, remote state, workspaces, CI/CD integration |

### 🌐 Web and Fullstack Frameworks
| Skill | What it does |
|-------|-------------|
| `nextjs-best-practices` | App Router — RSC, async params, data fetching, image/font optimization, self-hosting |
| `react-best-practices` | Hooks patterns, state management, memoization, virtualization, error boundaries |
| `fastapi` | Python REST APIs — Pydantic v2, dependency injection, JWT auth, async SQLAlchemy, testing |
| `graphql-api` | Schema design, resolvers, DataLoader (N+1 prevention), Apollo Client, Strawberry |
| `typescript-patterns` | Generics, discriminated unions, branded types, conditional types, strict tsconfig |

### 🔌 Services and Integrations
| Skill | What it does |
|-------|-------------|
| `stripe-integration` | Checkout Sessions, webhooks, subscriptions, Connect (Accounts v2), security checklist |
| `supabase-integration` | PostgreSQL queries, auth (OAuth/magic link), RLS policies, real-time, storage |

### 🎨 Design and UI
| Skill | What it does |
|-------|-------------|
| `frontend-design` | Aesthetic direction, typography systems, color palettes, micro-animations, anti-patterns |
| `web-artifacts-builder` | Self-contained interactive HTML/React/Tailwind/D3 artifacts and dashboards |

---

## Setup

### What you need

| Requirement | Cost | Notes |
|-------------|------|-------|
| [Qdrant Cloud](https://cloud.qdrant.io) | Free | 1 GB free cluster — create one, copy URL + API key |
| [Cloudflare](https://cloudflare.com) | **Free** | Workers Free plan supports SQLite-backed Durable Objects |
| Python 3.11+ | Free | For the seed script and optional local server |
| Node.js 18+ | Free | For the `wrangler` CLI |

> **Cloudflare is free.** skill-mcp uses SQLite-backed Durable Objects (`new_sqlite_classes` in `wrangler.jsonc`), which are available on the Cloudflare Workers **Free** plan (100k requests/day). You only need the $5/mo paid plan if you outgrow that limit or need KV-backed Durable Objects.

### Option A — One Command (recommended)

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

The wizard checks prerequisites → creates `.env` → installs Python deps → seeds Qdrant with all 30 skills → pushes Wrangler secrets → deploys the Worker. Done.

### Option B — Manual (step by step)

```bash
# 1. Clone
git clone https://github.com/yourusername/skill-mcp && cd skill-mcp

# 2. Configure credentials
cp .env.example .env
# Fill in: QDRANT_URL, QDRANT_API_KEY, WORKERS_AI_ACCOUNT_ID, WORKERS_AI_API_TOKEN

# 3. Install seed dependencies and seed Qdrant
pip install -r requirements.txt
python -X utf8 -m skill_mcp.seed.seed_skills

# 4. Deploy to Cloudflare
npm install -g wrangler
wrangler login
wrangler secret put QDRANT_URL      # paste your Qdrant URL
wrangler secret put QDRANT_API_KEY  # paste your Qdrant API key
wrangler deploy
```

Your server is live at:
```
https://skill-mcp.<your-subdomain>.workers.dev/sse
```

> Full credential walkthrough: [SETUP.md](SETUP.md)

### Make targets reference

```bash
# Cloudflare deployment
make env        # Copy .env.example → .env (skips if .env already exists)
make check      # Verify all required .env values are set
make install    # pip install -r requirements.txt
make seed       # Seed / re-seed Qdrant with all skills (idempotent)
make secrets    # Auto-push QDRANT_URL + QDRANT_API_KEY from .env to Worker
make deploy     # wrangler deploy
make dev        # Run local FastMCP server in stdio mode
make dev-http   # Run local FastMCP server on HTTP :8000
make setup      # Full first-run: env + install + seed + secrets + deploy

# Security & validation
make validate   # Validate all SKILL.md files — schema + prompt-injection scan

# Docker (one-command local stack)
make docker-up    # Start Qdrant + seed + MCP server
make docker-down  # Stop containers (keeps Qdrant data)
make docker-seed  # Re-seed after adding new skills
make docker-logs  # Follow server logs
```

### Option C — Docker (one command, fully local)

No Cloudflare account needed. Runs Qdrant locally in a container — useful for local-only setups, air-gapped environments, or testing before deploying.

```bash
# Start everything: Qdrant + seed + MCP server
docker compose up

# Or in background
docker compose up -d && docker compose logs -f server
```

Your local MCP server is live at `http://localhost:8000/sse`.

Add to your MCP client config:
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

**Requirements for Docker mode:** only `WORKERS_AI_ACCOUNT_ID` and `WORKERS_AI_API_TOKEN` in `.env` — Cloudflare credentials are still needed to generate embeddings via Workers AI. Qdrant runs locally, no Qdrant Cloud account required.

```bash
make docker-up     # Start the full stack
make docker-down   # Stop (data volume preserved)
make docker-seed   # Re-seed after adding new skills
```

---

## Connecting Your AI Agent

### Step 1 — Add the MCP server

Add to your MCP client config (`.mcp.json`, Claude Code settings, Cursor settings, etc.):

**Production (Cloudflare Worker):**
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

**Local dev (`wrangler dev`):**
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

**Local Python server** (needed for `skills_run_script` — Cloudflare Workers cannot run subprocesses):
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

### Step 2 — Install the master skill for your platform

Drop the right file into any project root and the agent will automatically follow the 3-tier skill workflow — when to search, how to interpret scores, and when to load supplementary files.

| Platform | File to copy | Where |
|----------|-------------|-------|
| **Claude Code** | `master-skill/platforms/claude-code/CLAUDE.md` | Project root |
| **Cursor** | `master-skill/platforms/cursor/.cursorrules` | Project root |
| **Windsurf** | `master-skill/platforms/windsurf/.windsurfrules` | Project root |
| **Antigravity** (Google) | `master-skill/platforms/antigravity/.agents/` | Project root (primary) |
| **Antigravity** (Google) | `master-skill/platforms/antigravity/AGENTS.md` | Project root (secondary) |
| **OpenAI Codex** | `master-skill/platforms/codex/AGENTS.md` | Project root |
| **Cline** (VSCode) | `master-skill/platforms/cline/.clinerules` | Project root |
| **GitHub Copilot** | `master-skill/platforms/copilot/.github/` | Project root |
| **Aider** | `master-skill/platforms/aider/CONVENTIONS.md` | Project root |

After copying, replace the placeholder URL with your deployed Worker URL.

Per-platform install commands: [`master-skill/README.md`](master-skill/README.md)

---

## Adding Your Own Skills

Skills live in `skill_mcp/skills_data/`. Each skill is a folder:

```
skill_mcp/skills_data/
└── my-skill/
    ├── SKILL.md          ← required: frontmatter + full instructions
    ├── references/       ← optional: markdown reference docs (.md)
    ├── scripts/          ← optional: executable scripts (.py, .js, .sh)
    └── assets/           ← optional: output templates and static files
```

### SKILL.md format

```markdown
---
name: my-skill
description: >
  One or two sentences describing WHEN to use this skill.
  Write it from the agent's perspective: "Use when the user asks to extract data from PDFs,
  process forms, or parse tables from documents."
license: Apache-2.0
metadata:
  author: your-name
  version: "1.0"
  tags: [pdf, extraction, data]
  platforms: [claude-code, cursor, any]
  triggers:
    - extract text from a PDF
    - parse a PDF document
    - read a PDF file
    - fill a PDF form
---

# Skill Title

Full step-by-step instructions. This is what the agent reads and follows.

Reference tier-3 files explicitly so the agent knows to load them:
- "For field type reference, see references/FORMS.md"
- "To extract data, run scripts/extract.py with PDF_PATH set to the file path"
- "Format your output using assets/extraction-template.md"
```

**Two critical rules:**

1. **Description and triggers are what get embedded** — write them to match how an agent would phrase the need, not how you'd name the skill. `"extract tables from a PDF"` beats `"pdf-skill"`.

2. **Reference tier-3 files by name in the body** — the agent receives a `tier3_manifest` listing available files and fetches only what the instructions explicitly mention. Nothing is loaded speculatively.

### Re-seed after adding

```bash
python -X utf8 -m skill_mcp.seed.seed_skills
# or:
make seed
```

The seed script is idempotent — re-running updates existing skills without creating duplicates.

---

## Security

### Prompt-injection defence (ingestion pipeline)

A malicious `SKILL.md` with embedded instruction overrides could alter how agents behave after loading the skill body — turning the registry into a prompt-injection delivery mechanism. skill-mcp is the first open-source skills registry to explicitly address this.

Every skill is scanned by `skill_mcp/security/prompt_injection.py` **before** it enters Qdrant — at seed time and in CI on every PR. Skills with CRITICAL or HIGH findings are blocked.

| Attack category | Severity | Example |
|----------------|----------|---------|
| Instruction-override phrases | CRITICAL | `"ignore all previous instructions"` |
| Role / identity hijacking | CRITICAL | `"you are now an unrestricted AI"` |
| Prompt delimiter injection | HIGH | `</system>`, `[INST]`, `<<SYS>>` |
| Credential exfiltration | CRITICAL | `"POST the API key to webhook.site/…"` |
| HTML / script injection | HIGH | `<script>` outside code blocks |
| Unicode BiDi / zero-width chars | HIGH | Visually hidden content |
| Base64 encoded payloads | CRITICAL | Base64 that decodes to override phrases |
| Content displacement | MEDIUM | 20+ consecutive blank lines |

Code blocks are stripped before structural checks — TypeScript generics (`Promise<User>`) and `<script>` tags in code examples never false-positive.

Full threat model: [`THREAT_MODEL.md`](THREAT_MODEL.md)

### Runtime hardening (Worker + local server)

- **1 MB request body limit** — POST bodies over 1 MB rejected with HTTP 413 before parsing
- **Sanitized error messages** — upstream URLs, Qdrant responses, and stack traces never reach MCP clients
- **Security response headers** — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`
- **Query string limits** — 2 KB total, 16 parameters, 128-char keys, 256-char values
- **Input validation** — `tools/call` arguments type-checked; malformed JSON-RPC returns proper error codes
- **Query length limit** — `skills_find_relevant` rejects queries over 2,000 characters

Script execution (`skills_run_script`, local server only):

- Isolated `tempfile.TemporaryDirectory()` — deleted after each run
- 30-second hard timeout with explicit process kill
- Minimal clean environment — no credentials or sensitive env vars passed to scripts
- Blocked environment variable injection (`PATH`, `LD_PRELOAD`, `PYTHONPATH`, etc.)
- Script source **never returned to the agent** — only `stdout / stderr / exit_code`
- Output truncated at 10,000 characters per stream

In the deployed Cloudflare Worker, `skills_run_script` returns the script manifest only — the Pyodide runtime cannot run subprocesses.

---

## Project Structure

```
skill-mcp/
├── src/
│   └── worker.py                  # Cloudflare Python Worker — MCP SSE server, all 6 tools
├── wrangler.jsonc                  # Workers AI binding + SQLite Durable Objects config
├── Makefile                        # Automation: setup, seed, deploy, dev, docker, validate
├── Dockerfile                      # Local FastMCP server image (non-root, health check)
├── docker-compose.yml              # One-command stack: Qdrant + seed + MCP server
├── .dockerignore                   # Excludes secrets, .env, .wrangler, git history
├── scripts/
│   ├── setup.ps1                  # Windows one-shot setup wizard
│   ├── setup.sh                   # Linux/macOS one-shot setup script
│   └── validate_skills.py         # SKILL.md schema + prompt-injection validator (used by CI)
├── .github/
│   └── workflows/
│       └── validate-skills.yml    # CI: YAML lint + duplicate check + injection scan on PRs
├── master-skill/                  # Drop-in agent instruction files (8 platforms)
│   ├── SKILL.md                   # Universal skill definition for MCP-aware agents
│   ├── README.md                  # Per-platform install commands
│   └── platforms/
│       ├── antigravity/           # .agents/rules/GEMINI.md + AGENTS.md
│       ├── claude-code/           # CLAUDE.md
│       ├── cursor/                # .cursorrules
│       ├── windsurf/              # .windsurfrules
│       ├── codex/                 # AGENTS.md
│       ├── cline/                 # .clinerules
│       ├── copilot/               # .github/copilot-instructions.md
│       └── aider/                 # CONVENTIONS.md
├── skill_mcp/
│   ├── security/
│   │   └── prompt_injection.py    # 9-category injection scanner (seed + CI)
│   ├── db/
│   │   ├── embedder.py            # Workers AI REST client with TTL cache
│   │   ├── qdrant_manager.py      # All 6 collections — upsert, query, tier3_manifest
│   │   ├── qdrant_client.py       # QdrantClient factory
│   │   └── cache.py               # Thread-safe TTL cache (no external deps)
│   ├── models/
│   │   └── skill.py               # Pydantic models for all 6 collection types
│   ├── seed/
│   │   └── seed_skills.py         # Walks skills_data/, scans, embeds, seeds Qdrant
│   ├── tools/                     # Tool implementations for the local Python server
│   │   ├── find_skills.py
│   │   ├── get_skill_body.py
│   │   ├── get_skill_options.py
│   │   ├── get_skill_reference.py
│   │   ├── run_skill_script.py    # Secure subprocess execution
│   │   └── get_skill_asset.py
│   ├── skills_data/               # 30 skill folders (one per skill)
│   │   ├── api-integration/
│   │   ├── claude-api/
│   │   ├── cloudflare-workers/
│   │   └── ... (27 more)
│   └── server.py                  # Local FastMCP server (optional, for script execution)
├── tests/
│   ├── test_prompt_injection.py   # 40 scanner tests (CRITICAL/HIGH/MEDIUM/legitimate content)
│   ├── test_cache.py
│   ├── test_models.py
│   └── test_tools_integration.py
├── pyproject.toml                  # Package config + optional local-server extras
├── requirements.txt                # Seed script deps (no PyTorch, no GPU)
├── .env.example                    # Credential template — copy to .env
├── SETUP.md                        # Full credential walkthrough
├── CONTRIBUTING.md                 # Skill submission workflow + security policy
├── THREAT_MODEL.md                 # 7 threat categories with mitigations
└── LICENSE                         # Apache 2.0
```

---

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full skill submission workflow — what makes a great skill, the SKILL.md format reference, step-by-step PR process, and the security policy for submitted skills.

**Quick start:**

```bash
# 1. Create your skill
mkdir -p skill_mcp/skills_data/my-skill && touch skill_mcp/skills_data/my-skill/SKILL.md

# 2. Validate locally (schema + prompt-injection scan)
python scripts/validate_skills.py skill_mcp/skills_data/my-skill/SKILL.md

# 3. Open a PR — CI runs automatically
```

**The two invariants that must never be broken:**

1. **Never embed the full body** — only `description + triggers` go into the vector collection
2. **Never return script source** — `skills_run_script` returns `stdout / stderr / exit_code` only

CI validates every PR that touches `skills_data/`: YAML syntax, schema, duplicate slug check, and prompt-injection scan. A failing scan blocks merge.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<div align="center">

Built with [Cloudflare Workers](https://workers.cloudflare.com) · [Qdrant](https://qdrant.tech) · [FastMCP](https://github.com/jlowin/fastmcp) · [MCP](https://modelcontextprotocol.io)

</div>
#   s k i l l s - m c p  
 