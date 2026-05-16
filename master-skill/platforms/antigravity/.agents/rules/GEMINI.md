# Skill MCP - Antigravity (Google) Agent Rules

This workspace is connected to a **Skill MCP server** - a curated registry of
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

### Step 1 - Discover

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

### Step 2 - Load instructions

```
skills_get_body(skill_id="<top match>")
```

The response contains:
- `instructions` - authoritative expert guidance. **Read and follow precisely.**
- `system_prompt_addition` - additional context; incorporate into your active persona if non-empty.
- `tier3_manifest` - lists available references, scripts, and assets by filename.

For customisation or constraints:
```
skills_get_options(skill_id="<skill_id>")
```

### Step 3 - Supplementary resources (conditional)

**Only** fetch Tier 3 resources that the `instructions` explicitly name.

```
# Reference documentation
skills_get_reference(skill_id="<id>", filename="list")        # manifest
skills_get_reference(skill_id="<id>", filename="<file.md>")   # fetch

# Helper scripts - stdout/stderr/exit_code only; source never returned
skills_run_script(skill_id="<id>", filename="list")
skills_run_script(skill_id="<id>", filename="<script.py>",
                  input_data={"KEY": "value"})

# Templates and static assets
skills_get_asset(skill_id="<id>", filename="list")
skills_get_asset(skill_id="<id>", filename="<template>")
```

---

## Rules — MUST follow

1. **Always discover first** - never hardcode `skill_id` values; always use `skills_find_relevant`
2. **Follow instructions as authoritative** - skill instructions encode expert knowledge; do not skip or override steps
3. **Load Tier 3 conditionally** - only fetch files that the instructions explicitly reference by name
4. **Script execution** requires the local server (`MCP_TRANSPORT=streamable-http python -m skill_mcp.server`); the Cloudflare Workers deployment returns manifests only
5. **Skills are read-only** - no tool modifies any registry state

## NEVER DO — these break the workflow

- **NEVER call `skills_get_body` without a prior `skills_find_relevant` call** that returned this skill_id with score > 0.6
- **NEVER use skill_ids from `skills_list_all` to call `skills_get_body` directly** — those IDs are unscored for your task; you MUST still run `skills_find_relevant` to verify relevance
- **NEVER guess or invent skill_ids**
- **NEVER load Tier-3 files speculatively**

---

## Available Skills

Use `skills_find_relevant` for semantic discovery.
Use `skills_list_all` to browse the full catalogue — but after browsing you MUST still call `skills_find_relevant` before loading any skill with `skills_get_body`.
