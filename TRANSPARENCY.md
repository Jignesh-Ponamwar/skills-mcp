# Transparency — skill-mcp Hosted Instance

This document describes what the hosted skill-mcp instance is, how it is operated, what guarantees it offers, and what trust decisions you are making when you connect an AI agent to it.

Read this before connecting any agent to a hosted skill-mcp endpoint you do not control.

---

## What "hosted" means here

The hosted instance at `skill-mcp.<subdomain>.workers.dev` is a **personal project deployment** run by the repository owner. It is:

- A single Cloudflare Worker backed by a single Qdrant Cloud cluster
- Operated by one person, with no operations team, no on-call rotation, and no SLA
- Not affiliated with Anthropic, Cloudflare, or any other organization
- Free to use but offered without any guarantee of availability, correctness, or continued operation

If you need reliability guarantees, auditability, or control over what skills are loaded into your agents, you should **self-host**. The setup takes under 10 minutes. See [SETUP.md](SETUP.md).

---

## No SLA — Explicit Statement

> **There is no Service Level Agreement for the hosted instance.**

- Uptime is best-effort. The instance may be unavailable without notice.
- Skills may be updated, added, or removed without versioned deprecation notice.
- The Qdrant cluster backing the instance may be replaced, migrated, or paused.
- The Worker may be redeployed at any time, terminating active SSE sessions.

If your workflow depends on this server being available, use your own deployment.

---

## Skills Available on the Hosted Instance

The hosted instance runs the bundled skills from this repository. The skill set reflects the current state of the `main` branch.

**Last verified against main:** See [git log](https://github.com/Jignesh-Ponamwar/skills-mcp/commits/main) for the latest commit date.

| Category | Skills |
|----------|--------|
| Core Development | `api-integration`, `code-review`, `data-analysis`, `readme-writer`, `sql-query-writer`, `test-writer`, `web-scraper` |
| Documents | `docx-creator`, `pdf-processing`, `pptx-creator`, `xlsx-creator` |
| AI / LLM | `claude-api`, `gemini-api`, `openai-api`, `llm-prompt-engineering`, `mcp-server-builder` |
| Cloud / Infrastructure | `cloudflare-workers`, `docker-containerization`, `github-actions`, `terraform` |
| Web / Fullstack | `nextjs-best-practices`, `react-best-practices`, `fastapi`, `graphql-api`, `typescript-patterns` |
| Services | `stripe-integration`, `supabase-integration` |
| Design / UI | `frontend-design`, `web-artifacts-builder` |
| Utilities | `git-commit-writer` |

The complete skill list and current frontmatter can be inspected at: [`skill_mcp/skills_data/`](skill_mcp/skills_data/)

---

## Security Scanning Status

Every skill in the hosted instance was scanned by the automated prompt-injection scanner before being seeded into Qdrant. The scanner covers:

| Attack category | Severity | Blocks ingestion? |
|----------------|----------|------------------|
| Instruction-override phrases | CRITICAL | Yes |
| Role / identity hijacking | CRITICAL | Yes |
| Prompt delimiter injection | HIGH | Yes |
| Credential exfiltration patterns | CRITICAL | Yes |
| HTML / script injection | HIGH | Yes |
| Unicode BiDi / zero-width attacks | HIGH | Yes |
| Base64 payloads decoding to overrides | CRITICAL | Yes |
| Content displacement (≥20 blank lines) | MEDIUM | No (flagged only) |

Scanner source: [`skill_mcp/security/prompt_injection.py`](skill_mcp/security/prompt_injection.py)

**What the scanner does not cover:**

The scanner uses pattern matching, not semantic understanding. A carefully crafted skill body could potentially evade detection while still influencing agent behavior. LLM-assisted semantic review is a [planned improvement](THREAT_MODEL.md#threat-category-1-prompt-injection-via-skillmd).

For production environments handling sensitive tasks, self-hosting with your own curated skill set is the appropriate choice.

---

## Deployment Model

```
Your AI agent (MCP client)
        │
        │  MCP over SSE or Streamable HTTP (HTTPS)
        ▼
Cloudflare Worker (Python/Pyodide)
  — single Durable Object instance
  — holds SSE session state (in-memory, not persisted)
  — no authentication on any endpoint
  — per-IP rate limiting: 60 req/min (configurable via RATE_LIMIT_RPM)
  — CORS headers on all responses (supports browser-based MCP clients)
        │                │
        │ HTTPS REST     │ Workers AI binding
        ▼                ▼
  Qdrant Cloud      Workers AI
  (6 collections)   (bge-small-en-v1.5)
```

**There is no authentication on the `/sse` or `/mcp` endpoints.** Anyone who knows the Worker URL can connect and call all six MCP tools. A per-IP sliding-window rate limit (60 requests/minute by default, configurable via `RATE_LIMIT_RPM`) is enforced at the application level.

**Transports:** The Worker supports two MCP transports:
- **SSE** (`GET /sse` + `POST /messages/`) — MCP spec revision `2024-11-05`; used by Claude Desktop and Claude.ai
- **Streamable HTTP** (`POST /mcp`, stateless) — MCP spec revision `2025-03-26`; used by browser-based testers (Glama, MCP Inspector) and newer SDK clients

CORS headers (`Access-Control-Allow-Origin: *`) are included on all responses to support browser-based clients.

---

## Trust Boundaries

Connecting an AI agent to any external MCP server — including this one — means that server's responses flow directly into your agent's context window. You are trusting that:

1. **Skill bodies do not contain prompt injection.** The scanner reduces this risk but cannot eliminate it entirely.
2. **Scripts are not executed via the hosted instance.** `skills_run_script` returns a manifest only on the Cloudflare Worker — execution requires the local Python server. No code runs server-side from tool calls against the hosted instance.
3. **The operator does not modify skills to manipulate agent behavior.** This is a trust-in-operator assumption you must make for any third-party MCP server.
4. **The Qdrant cluster has not been compromised.** If the Qdrant API key were compromised, an attacker with write access could inject malicious skill content that bypasses the scanner.

**Recommendation for sensitive workloads:** Self-host. The `docker compose up` path runs everything locally in under 5 minutes and requires no Cloudflare account. See [SETUP.md](SETUP.md).

---

## Rate Limiting and Abuse Prevention

The hosted instance enforces a **per-IP sliding-window rate limit of 60 requests/minute** at the application level. The limit is configurable via the `RATE_LIMIT_RPM` environment variable for self-hosted deployments. When the limit is exceeded, the Worker returns HTTP 429. The rate state is held in the Durable Object closure and is not persisted — it resets on Worker restart.

Cloudflare platform-level protections (DDoS mitigation, automated bot scoring) are also active.

If sustained abuse causes the free-tier Cloudflare limits (100k requests/day) to be exceeded, the instance will stop responding until the next day's quota resets.

For teams or high-frequency workflows, self-host to avoid shared quota exhaustion and to set your own rate limit.

---

## What Happens When Skills Are Updated

When skills in this repository are updated and the seed script is re-run:

- The **latest-alias** Qdrant point for each skill is overwritten with the new content
- A **versioned point** (`skill_id@version`) is also written and retained — old versions are kept until explicitly pruned via `make seed-prune` (planned target)
- Active agent sessions that already loaded a skill body are not affected (the body was copied into context)
- Future `skills_get_body` calls return the latest version by default; specific versions can be requested with the `version` parameter or inline `skill_id@version` notation

Skill versioning is implemented. See [docs/VERSIONING.md](docs/VERSIONING.md) for details including pinning, fallback behavior, and deprecation notices.

---

## Reporting Problems

- **Security issues:** Do not open public GitHub issues. Email the maintainer (address in GitHub profile) privately.
- **Incorrect or outdated skill content:** Open a GitHub issue or PR.
- **Hosted instance downtime:** No formal reporting mechanism exists — this is an unmonitored personal deployment.

See [THREAT_MODEL.md](THREAT_MODEL.md) for the full security model and residual risks.

---

*Last reviewed: 2026-05-02*
