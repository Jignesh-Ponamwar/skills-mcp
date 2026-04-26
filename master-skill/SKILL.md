---
name: skill-mcp-master
description: >
  Master reference for the Skill MCP server — a self-hosted agent skills registry
  that delivers curated, expert instructions for common AI tasks via 6 MCP tools.
  Covers the full 3-tier progressive disclosure workflow: Tier 1 discovery
  (skills_find_relevant), Tier 2 loading (skills_get_body, skills_get_options),
  and Tier 3 supplementary resources (skills_get_reference, skills_run_script,
  skills_get_asset). Use this skill whenever you need to understand, operate, or
  get the most out of the Skill MCP server.
license: Apache-2.0
metadata:
  author: skill-mcp
  version: "1.0"
  tags: [mcp, skills, workflow, meta, reference, registry]
  platforms: [claude-code, cursor, windsurf, codex, cline, copilot, aider, any]
  triggers:
    - how do I use the skill MCP
    - what skills are available
    - skill workflow
    - MCP skills reference
    - use a skill
    - check skills
    - find a skill for this task
---

# Skill MCP — Master Usage Guide

## What Is the Skill MCP?

The Skill MCP server is a **self-hosted agent skills registry** accessible to any
MCP-compatible AI agent or tool. It stores curated, expert-authored instruction sets
("skills") and delivers them on demand through a structured 3-tier disclosure model.

Each skill contains:

| Tier | Content | Tools |
|------|---------|-------|
| 1 | Frontmatter — name, description, tags, score | `skills_find_relevant` |
| 2 | Instructions, system prompt addition | `skills_get_body`, `skills_get_options` |
| 3 | Reference docs, executable scripts, asset templates | `skills_get_reference`, `skills_run_script`, `skills_get_asset` |

---

## The Canonical 3-Step Workflow

Follow this sequence for every task where a skill might apply.

### Step 1 — Discover (`skills_find_relevant`)

```
skills_find_relevant(query="<specific description of your task>", top_k=5)
```

**Interpret scores:**
- `score > 0.6` → strong match — proceed to Step 2
- `score 0.4–0.6` → possible match — read description to decide
- `score < 0.4` → no relevant skill — proceed without one

**Query tips:**
- ✅ `"write pytest unit tests for a Flask REST API endpoint"`
- ✅ `"extract tables from a multi-page PDF and output as CSV"`
- ✅ `"review Python code for security vulnerabilities"`
- ❌ `"testing"` (too generic — poor embedding)
- ❌ `"help me"` (no task signal)

---

### Step 2 — Load (`skills_get_body`)

```
skills_get_body(skill_id="<top result from Step 1>")
```

The response contains:

```json
{
  "skill_id": "test-writer",
  "instructions": "## Testing Workflow\n1. Identify the function under test ...",
  "system_prompt_addition": "You are a senior test engineer ...",
  "tier3_manifest": {
    "references": ["TESTING-GUIDE.md", "COVERAGE-POLICY.md"],
    "scripts":    ["coverage_check.py"],
    "assets":     ["test-template.py"]
  }
}
```

**After loading:**
1. Read and apply `instructions` — this is the authoritative guidance
2. If `system_prompt_addition` is non-empty, incorporate it into your context
3. Check `tier3_manifest` — only proceed to Step 3 if instructions reference specific files

**Optional: load config** (`skills_get_options`)
```
skills_get_options(skill_id="<skill_id>")
```
Only needed when customising skill behaviour or checking constraints/dependencies.

---

### Step 3 — Supplement (only when needed)

**3a — Reference documents:**
```
# First: get the manifest
skills_get_reference(skill_id="test-writer", filename="list")
# Then: fetch the specific file the instructions mentioned
skills_get_reference(skill_id="test-writer", filename="TESTING-GUIDE.md")
```

**3b — Execute a helper script:**
```
# First: see available scripts
skills_run_script(skill_id="test-writer", filename="list")
# Then: run with optional inputs
skills_run_script(skill_id="test-writer", filename="coverage_check.py",
                  input_data={"TARGET_DIR": "./src", "MIN_COVERAGE": "80"})
# Returns: exit_code, stdout, stderr — source is never exposed
```

**3c — Fetch a template or asset:**
```
# First: get the manifest
skills_get_asset(skill_id="test-writer", filename="list")
# Then: fetch the template
skills_get_asset(skill_id="test-writer", filename="test-template.py")
# Use as a starting template — adapt it to the specific task
```

> **Rule:** Only load Tier 3 resources that the Tier 2 instructions explicitly
> reference. Do not load them speculatively — it wastes context and latency.

---

## Complete Example

```
# 1. Discover
results = skills_find_relevant(
    query="write integration tests for a Python REST API using pytest"
)
# → test-writer: 0.84  ← strong match

# 2. Load instructions
body = skills_get_body(skill_id="test-writer")
# → instructions: "## Testing Workflow ..."
# → tier3_manifest.references: ["TESTING-GUIDE.md"]
# → tier3_manifest.assets: ["test-template.py"]

# 3. The instructions say "follow TESTING-GUIDE.md for project conventions"
guide = skills_get_reference(skill_id="test-writer", filename="TESTING-GUIDE.md")

# 4. The instructions say "use test-template.py as your file scaffold"
template = skills_get_asset(skill_id="test-writer", filename="test-template.py")

# 5. Apply instructions using the guide and template
```

---

## Decision Rules

| Situation | Action |
|-----------|--------|
| Starting any non-trivial task | Always call `skills_find_relevant` first |
| All scores < 0.4 | No relevant skill — proceed without one |
| Score > 0.4 | Call `skills_get_body` to load instructions |
| Instructions are complete | Apply them — stop, do not load Tier 3 |
| Instructions mention a file | Load that specific file via Tier 3 |
| User asks to customise skill | Call `skills_get_options` |
| Task is trivial (< 2 min) | Skip skill lookup if confidence is high |

---

## Available Skills (current registry)

| skill_id | Domain |
|----------|--------|
| `api-integration` | REST/GraphQL API integration patterns |
| `code-review` | Security, quality, and bug review |
| `data-analysis` | CSV/tabular data analysis and EDA |
| `docx-creator` | Word document generation |
| `git-commit-writer` | Conventional commit messages |
| `pdf-processing` | PDF extraction and form filling |
| `readme-writer` | Project README generation |
| `sql-query-writer` | SQL query authoring and validation |
| `test-writer` | Unit, integration, and E2E test writing |
| `web-scraper` | Web scraping and data extraction |

*Query `skills_find_relevant` for semantic discovery — the above is a reference snapshot.*

---

## Tool Quick-Reference

| Tool | When to call | Returns |
|------|-------------|---------|
| `skills_find_relevant(query, top_k=5)` | Start of every task | Ranked skill list with scores |
| `skills_get_body(skill_id)` | After finding a match | Instructions + tier3_manifest |
| `skills_get_options(skill_id)` | When customising behaviour | Config schema, variants, limits |
| `skills_get_reference(skill_id, filename="list")` | To see/fetch reference docs | Manifest or file content |
| `skills_run_script(skill_id, filename, input_data={})` | To run a helper script | exit_code, stdout, stderr |
| `skills_get_asset(skill_id, filename="list")` | To see/fetch templates | Manifest or file content |

---

## Notes

- Skills are **read-only** — calling any tool does not modify registry state
- **Script execution** is only available on the **local server**
  (`MCP_TRANSPORT=streamable-http python -m skill_mcp.server`).
  The Cloudflare Workers deployment returns the script manifest only.
- Skills are versioned — `skills_get_options` returns the version of each skill
- The MCP server URL for SSE transport:
  `https://skill-mcp.<your-subdomain>.workers.dev/sse`
