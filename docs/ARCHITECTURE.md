# Architecture Reference

This document describes what the system actually does in each deployment mode. It is intended as the honest source of truth — if this document and the code disagree, the code is right and this document needs updating.

---

## Deployment Modes

There are three distinct deployment modes. They share the same skill data and Qdrant backend, but differ in runtime, transport, and feature support.

### Mode 1: Cloudflare Worker (deployed)

```
AI Agent / MCP Client
      │
      │  HTTPS
      ▼
Cloudflare Worker (Python/Pyodide)
  ├── Transport A: SSE  (GET /sse + POST /messages/)     ← Claude Desktop / Claude.ai
  ├── Transport B: Streamable HTTP  (POST /mcp, stateless) ← Glama / MCP Inspector / new SDKs
  ├── CORS: Access-Control-Allow-Origin: * on all responses
  ├── Rate limit: 60 req/min per IP (configurable via RATE_LIMIT_RPM)
  ├── Embedding: Workers AI binding (bge-small-en-v1.5, 384-dim)
  ├── State: Durable Object (in-memory asyncio.Queue per SSE session)
  └── Storage: Qdrant Cloud (read-only at runtime)
```

**What works:** all six MCP tools — `skills_find_relevant`, `skills_get_body` (with optional `version` parameter), `skills_get_options`, `skills_get_reference`, `skills_run_script` (list mode only), `skills_get_asset`

**What does not work:** `skills_run_script` execution mode — returns a manifest with a note explaining why. The Pyodide runtime does not support `subprocess`.

**Deploy command:** `wrangler deploy`

---

### Mode 2: Local Python Server (HTTP)

```
AI Agent / MCP Client
      │
      │  HTTP (streamable-http, localhost only by default)
      ▼
FastMCP server (Python, skill_mcp/server.py)
  ├── Transport: streamable-http  (MCP_TRANSPORT=streamable-http)
  ├── Embedding: Workers AI REST API (requires WORKERS_AI_* credentials)
  ├── State: none (stateless HTTP)
  └── Storage: Qdrant Cloud (read + write access for seed operations)
```

**What works:** all six MCP tools including `skills_run_script` execution mode

**What does not work:** nothing — this is the full-feature deployment

**Start command:** `make dev-http` (sets `MCP_TRANSPORT=streamable-http`)

---

### Mode 3: Local Python Server (stdio)

```
AI Agent / MCP Client
      │
      │  stdin/stdout (JSON-RPC over stdio)
      ▼
FastMCP server (Python, skill_mcp/server.py)
  ├── Transport: stdio  (default, MCP_TRANSPORT unset)
  ├── Embedding: Workers AI REST API
  ├── State: none (stateless process per connection)
  └── Storage: Qdrant Cloud
```

**What works:** all six MCP tools including `skills_run_script` execution mode

**When to use:** Claude Code, Cursor, Windsurf, and other MCP clients that launch servers as child processes. The `command`/`args` MCP config format.

**Start command:** `make dev` or `python -m skill_mcp.server`

---

### Mode 4: Docker (local Qdrant)

```
AI Agent / MCP Client
      │
      │  HTTP (streamable-http, port 8000)
      ▼
FastMCP server (Python, skill_mcp/server.py)
  ├── Transport: streamable-http
  ├── Embedding: Workers AI REST API (still requires Cloudflare credentials)
  └── Storage: Qdrant (local container, port 6333)
```

**What works:** all six MCP tools including `skills_run_script` execution mode

**What is different from Mode 2:** Qdrant runs locally in a container, no Qdrant Cloud account needed. Workers AI credentials are still required for embedding.

**Start command:** `docker compose up`

---

## Feature Support Matrix

| Feature | Worker (deployed) | Local HTTP | Local stdio | Docker |
|---------|:-----------------:|:----------:|:-----------:|:------:|
| `skills_find_relevant` | ✅ | ✅ | ✅ | ✅ |
| `skills_get_body` | ✅ | ✅ | ✅ | ✅ |
| `skills_get_body` (version pinning) | ✅ | ✅ | ✅ | ✅ |
| `skills_get_options` | ✅ | ✅ | ✅ | ✅ |
| `skills_get_reference` | ✅ | ✅ | ✅ | ✅ |
| `skills_run_script` (list) | ✅ manifest only | ✅ | ✅ | ✅ |
| `skills_run_script` (execute) | ❌ Pyodide limit | ✅ | ✅ | ✅ |
| `skills_get_asset` | ✅ | ✅ | ✅ | ✅ |
| SSE transport | ✅ | ❌ | ❌ | ❌ |
| Streamable HTTP transport | ✅ | ✅ | ❌ | ✅ |
| stdio transport | ❌ | ❌ | ✅ | ❌ |
| Per-IP rate limiting | ✅ 60 req/min | ❌ | ❌ | ❌ |
| CORS headers | ✅ | ✅ | n/a | ✅ |
| Subprocess execution | ❌ | ✅ | ✅ | ✅ |
| No Qdrant Cloud account | ❌ | ❌ | ❌ | ✅ |
| No Cloudflare account | ❌ | ✅ | ✅ | ✅* |

*Docker still requires Workers AI credentials for embedding.

---

## Durable Objects — What They Actually Do

The Cloudflare Worker uses a single Durable Object (`SkillMCPServer`, class in `src/worker.py`). Here is exactly what it stores:

### What IS stored in the DO

1. **The ASGI app closure** (Python object, in-memory): the `_build_server(env)` return value. This holds the `_sessions` dict and all tool implementations as closures. It is created once per Worker process startup and lives for the lifetime of the DO instance.

2. **The `_sessions` dict** (Python dict, in-memory): maps `session_id → asyncio.Queue`. Each SSE connection creates one entry; disconnection removes it. This is ephemeral — a Worker restart clears all sessions.

### What IS NOT stored in the DO

- **No SQLite data.** The `new_sqlite_classes` migration tag in `wrangler.jsonc` is required by Cloudflare to register the DO class, but the SQLite storage API (`this.storage`) is never called. No data is written to durable storage.
- **No user data.** No request history, no tool call logs, no session metadata.
- **No skill data.** Skills live in Qdrant, not in the DO.

### Why the DO is necessary

Cloudflare Workers are stateless by default — each request may run in a different isolate. The SSE transport requires that `POST /messages/?sessionId=X` reach the same process as the original `GET /sse` that created session X. The DO singleton ensures all requests for a given `skill-mcp` name route to the same instance. Without it, POST requests would fail with "Session not found" because they land in a different isolate.

---

## Transport Status

### Current

| Deployment | Transport | MCP Spec | Status |
|------------|-----------|----------|--------|
| Cloudflare Worker | SSE (`GET /sse` + `POST /messages/`) | `2024-11-05` | Functional — used by Claude Desktop and Claude.ai |
| Cloudflare Worker | Streamable HTTP (`POST /mcp`, stateless) | `2025-03-26` | Implemented — used by Glama, MCP Inspector, newer SDK clients |
| Local Python server | `streamable-http` or `stdio` | `2025-03-26` | Current preferred transports |

### What SSE transport means

The SSE transport works as follows:

1. Agent opens `GET /sse` — server sends an `event: endpoint` with a `data:` line containing the messages URL (`/messages/?sessionId=<uuid>`)
2. Connection stays open; server pushes JSON-RPC responses as `data:` SSE events
3. Agent sends JSON-RPC requests via `POST /messages/?sessionId=<uuid>` (separate HTTP request)
4. Worker routes the POST to the matching open SSE session via the DO's `_sessions` dict

### What Streamable HTTP transport means (Worker)

The `POST /mcp` endpoint is a stateless JSON-RPC handler:

1. Client sends a single JSON-RPC message (e.g., `{"method": "tools/list", ...}`) as the POST body
2. Worker dispatches the message through the same tool dispatch logic as SSE
3. Worker returns a single JSON-RPC response directly in the HTTP response body
4. No session is created — each request is independent

This is simpler than SSE (no session routing, no DO session dict involvement) and required for browser-based testers that cannot establish persistent connections or lack SSE support. CORS preflight (`OPTIONS`) requests return 204 with CORS headers.

---

## Six Qdrant Collections — Responsibilities

| Collection | Has vectors? | Contents | Accessed by |
|-----------|:------------:|----------|-------------|
| `skill_frontmatter` | ✅ 384-dim | skill_id, name, description, tags, triggers, version, author | `skills_find_relevant` |
| `skill_body` | payload only | full markdown instructions, system_prompt_addition | `skills_get_body` |
| `skill_options` | payload only | config_schema, variants, dependencies, limitations | `skills_get_options` |
| `skill_references` | payload only | filename, content (markdown), description, file_path | `skills_get_reference` |
| `skill_scripts` | payload only | filename, language, source (never returned), description, dependencies | `skills_run_script` |
| `skill_assets` | payload only | filename, content, asset_type, description | `skills_get_asset` |

**Important:** `skill_scripts.source` is stored in Qdrant but never returned to MCP clients. The field is fetched internally for subprocess execution only. This is enforced in `run_skill_script.py` and `worker.py`.

The payload-only collections use a dummy 1-dim vector (`[0.0]`) at point creation — Qdrant requires a vector for every point, but these collections are accessed by scroll (filter by `skill_id`) not by search.

---

## Embedding Architecture

Both the Worker and the local server use the same embedding model: `@cf/baai/bge-small-en-v1.5` (384-dim). This model is called:

- **At seed time**: via the Cloudflare REST API (`https://api.cloudflare.com/client/v4/accounts/<id>/ai/run/<model>`) from the local seed script
- **At query time (Worker)**: via the Workers AI binding (`env.AI.run(model, input)`) — no REST call needed
- **At query time (local server)**: via the Cloudflare REST API — same call as seed time

This alignment ensures vectors are always comparable: seed-time embeddings and query-time embeddings are generated by the same model via the same provider. Changing the model requires re-seeding all skills from scratch.

---

## Seed Script

`skill_mcp/seed/seed_skills.py` is the ingestion pipeline. It:

1. Walks `skill_mcp/skills_data/` for `SKILL.md` files
2. Parses YAML frontmatter and markdown body
3. Runs the prompt-injection scanner — blocks skills with CRITICAL/HIGH findings
4. Calls Cloudflare Workers AI REST API to embed `description + triggers` for `skill_frontmatter`
5. Upserts all six collections in Qdrant (idempotent — re-running updates, does not duplicate)
6. Validates file paths with `Path.resolve()` to prevent path traversal

The seed script is run locally by operators, not by the deployed Worker. The Worker is read-only at runtime.

Versioning: the seed script writes two points per skill — a **latest alias** (deterministic ID from `skill_id`) and a **versioned point** (ID from `skill_id@version`). The latest alias is always overwritten; versioned points accumulate until pruned. See [VERSIONING.md](VERSIONING.md).

---

## Threshold Calibration

`skill_mcp/eval/calibrate.py` is a standalone calibration runner. It:

1. Loads `tests/eval/threshold_calibration.json` (120 eval triples — 90 strong-match + 30 true-negative)
2. Calls `skills_find_relevant` for each query
3. Sweeps `(t_high, t_low)` pairs in the range `[0.50–0.70] × [0.30–0.45]`
4. Reports precision, recall, F1, and specificity for each pair
5. Exits 0 if any pair meets the targets (precision ≥ 0.90, recall ≥ 0.85), exits 1 if not

Run with `make calibrate`. Requires live Qdrant access and a seeded registry. See [THRESHOLD_CALIBRATION.md](THRESHOLD_CALIBRATION.md) for full documentation.
