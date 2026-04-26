# Skill MCP — Agent Instructions for Claude Code

This project is connected to a **Skill MCP server** — a curated registry of expert
instruction sets for common AI tasks. Use it proactively to deliver higher-quality,
more consistent results.

---

## MCP Server

**Transport:** SSE
**URL:** `https://skill-mcp.<your-subdomain>.workers.dev/sse`

The server exposes 6 tools under the prefix `skills_`.

---

## When to Use Skills

Check for a relevant skill at the **start of any non-trivial task**:

- Writing or reviewing code
- Generating tests
- Analysing data (CSV, SQL, PDFs)
- Writing documentation (README, commit messages, API docs)
- Web scraping or API integration
- Creating documents (DOCX, reports)

Do not check for skills on simple questions, quick edits, or conversational replies.

---

## Canonical Workflow (always follow this order)

### 1 · Discover

```
skills_find_relevant(query="<specific description of what you need to do>")
```

Score thresholds:
- `> 0.6` → strong match → proceed to step 2
- `0.4 – 0.6` → read description to decide
- `< 0.4` → no skill available → proceed without one

**Write specific queries:** `"write pytest unit tests for a Flask REST endpoint"`
not `"testing"`.

### 2 · Load instructions

```
skills_get_body(skill_id="<top match>")
```

Returns `instructions` (apply these) and `tier3_manifest` (lists supplementary files).

Optionally load config/constraints if the user asks about customisation:
```
skills_get_options(skill_id="<skill_id>")
```

### 3 · Fetch supplementary resources (only if instructions reference them)

```
# Reference documents
skills_get_reference(skill_id="<id>", filename="<file.md>")

# Execute a helper script — returns stdout/stderr only, source never exposed
skills_run_script(skill_id="<id>", filename="<script.py>", input_data={})

# Templates and static assets
skills_get_asset(skill_id="<id>", filename="<template.md>")
```

Call `filename="list"` on any Tier 3 tool to get its manifest first.

> **Only load files that the instructions explicitly reference.** Do not load all
> available Tier 3 resources speculatively.

---

## Decision Table

| Signal | Action |
|--------|--------|
| New task, non-trivial | `skills_find_relevant` first |
| All scores < 0.4 | Proceed without skill |
| Score ≥ 0.4 | `skills_get_body` → apply instructions |
| `tier3_manifest` lists a file the instructions reference | Fetch that file |
| User asks to customise | `skills_get_options` |

---

## Available Skills (quick reference)

`api-integration` · `code-review` · `data-analysis` · `docx-creator` ·
`git-commit-writer` · `pdf-processing` · `readme-writer` ·
`sql-query-writer` · `test-writer` · `web-scraper`

*Use `skills_find_relevant` for semantic discovery — do not guess skill_ids.*

---

## Important Constraints

- **Script execution** requires the local server; the Cloudflare Worker returns manifest only
- Skills are read-only — no tool modifies registry state
- Treat skill `instructions` as authoritative expert guidance — follow them precisely
- `system_prompt_addition` from `skills_get_body` should be incorporated into your context
