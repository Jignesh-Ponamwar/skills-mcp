# Skill MCP — GitHub Copilot Custom Instructions

This repository is connected to a **Skill MCP server** that provides curated,
expert instruction sets for common engineering tasks. Consult it at the start of
non-trivial work to receive authoritative, task-specific guidance.

## MCP Server

- **URL:** `https://skill-mcp.<your-subdomain>.workers.dev/sse`
- **Transport:** SSE (MCP protocol)

## When to Use

Query the skills registry before starting any of these tasks:

| Task type | Example |
|-----------|---------|
| Testing | Write pytest unit/integration tests |
| Code review | Review code for security, bugs, quality |
| Data analysis | Analyse CSV data, write SQL queries |
| Documentation | Write README, commit messages, API docs |
| Document generation | Create DOCX reports |
| API work | Integrate REST/GraphQL APIs |
| Data extraction | Scrape web pages, extract PDF content |

## Workflow

**Step 1 — Check for a skill:**
```
skills_find_relevant(query="<specific task description>")
```
If the top score exceeds 0.4, load the skill. Below 0.4, no skill is available.

**Step 2 — Load instructions:**
```
skills_get_body(skill_id="<top match>")
```
Follow the `instructions` field precisely. Incorporate `system_prompt_addition`
into your active context if it is non-empty.

**Step 3 — Fetch supplementary files** (only if instructions name them):
```
skills_get_reference(skill_id, filename="<name.md>")   # reference docs
skills_get_asset(skill_id, filename="<template>")       # templates
skills_run_script(skill_id, filename="<script.py>",     # helper scripts
                  input_data={"KEY": "value"})
```

## Rules

1. Always use `skills_find_relevant` first — never hardcode `skill_id` values
2. Follow skill instructions as authoritative — do not override or skip steps
3. Only load Tier 3 resources that instructions explicitly reference
4. `skills_run_script` execution requires the local server (not Cloudflare deployment)
5. Skills are read-only — no tool modifies any state

## Available Skills

`api-integration` · `code-review` · `data-analysis` · `docx-creator` ·
`git-commit-writer` · `pdf-processing` · `readme-writer` ·
`sql-query-writer` · `test-writer` · `web-scraper`
