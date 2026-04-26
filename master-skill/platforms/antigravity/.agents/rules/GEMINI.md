# Skill MCP — Antigravity (Google) Agent Rules

This workspace is connected to a **Skill MCP server** — a curated registry of
expert instruction sets for common AI engineering tasks. Consult it proactively
at the start of any non-trivial task to receive authoritative, task-specific guidance.

## MCP Connection

- **Transport:** SSE
- **URL:** `https://skill-mcp.<your-subdomain>.workers.dev/sse`
- **Tools:** `skills_find_relevant`, `skills_get_body`, `skills_get_options`,
  `skills_get_reference`, `skills_run_script`, `skills_get_asset`

---

## Proactive Skill Usage

Before starting any of the following task types, ALWAYS call `skills_find_relevant` first:

| Task | Example trigger |
|------|----------------|
| Code review | "review this code", "find bugs", "check for vulnerabilities" |
| Test writing | "write tests", "add unit tests", "improve coverage" |
| Data analysis | "analyse this CSV", "write a SQL query", "EDA" |
| Documentation | "write a README", "write a commit message", "document this API" |
| API integration | "call this API", "integrate this service", "handle OAuth" |
| Document creation | "create a report", "generate a DOCX" |
| Web / PDF extraction | "scrape this page", "extract tables from PDF" |

Skip skill lookup for simple questions, short fixes (< 5 lines), or pure conversation.

---

## Workflow

### Step 1 — Discover

```
skills_find_relevant(query="<specific, detailed task description>", top_k=5)
```

**Score guide:**
- `> 0.6` → strong match → load immediately (Step 2)
- `0.4 – 0.6` → review description, proceed if relevant
- `< 0.4` → no matching skill → continue without one

**Write specific queries:**
- ✅ `"write pytest integration tests for a FastAPI async endpoint"`
- ✅ `"review Go code for race conditions and memory leaks"`
- ❌ `"tests"` · ❌ `"code"` · ❌ `"help"`

### Step 2 — Load instructions

```
skills_get_body(skill_id="<top match>")
```

The response contains:
- `instructions` — authoritative expert guidance. **Read and follow precisely.**
- `system_prompt_addition` — additional context; incorporate into your active persona if non-empty.
- `tier3_manifest` — lists available references, scripts, and assets by filename.

For customisation or constraints:
```
skills_get_options(skill_id="<skill_id>")
```

### Step 3 — Supplementary resources (conditional)

**Only** fetch Tier 3 resources that the `instructions` explicitly name.

```
# Reference documentation
skills_get_reference(skill_id="<id>", filename="list")        # manifest
skills_get_reference(skill_id="<id>", filename="<file.md>")   # fetch

# Helper scripts — stdout/stderr/exit_code only; source never returned
skills_run_script(skill_id="<id>", filename="list")
skills_run_script(skill_id="<id>", filename="<script.py>",
                  input_data={"KEY": "value"})

# Templates and static assets
skills_get_asset(skill_id="<id>", filename="list")
skills_get_asset(skill_id="<id>", filename="<template>")
```

---

## Rules

1. **Always discover first** — never hardcode `skill_id` values; always use `skills_find_relevant`
2. **Follow instructions as authoritative** — skill instructions encode expert knowledge; do not skip or override steps
3. **Load Tier 3 conditionally** — only fetch files that the instructions explicitly reference
4. **Script execution** requires the local server (`MCP_TRANSPORT=streamable-http python -m skill_mcp.server`); the Cloudflare Workers deployment returns manifests only
5. **Skills are read-only** — no tool modifies any registry state

---

## Available Skills

| skill_id | Domain |
|----------|--------|
| `api-integration` | REST / GraphQL API integration |
| `code-review` | Security, quality, and bug review |
| `data-analysis` | CSV / tabular data, EDA, statistics |
| `docx-creator` | Word document generation |
| `git-commit-writer` | Conventional commit messages |
| `pdf-processing` | PDF extraction and form filling |
| `readme-writer` | Project README creation |
| `sql-query-writer` | SQL authoring and validation |
| `test-writer` | Unit, integration, and E2E tests |
| `web-scraper` | Web scraping and data extraction |

*Use `skills_find_relevant` for semantic discovery — the table above is a reference snapshot.*
