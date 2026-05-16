# Skill MCP - GitHub Copilot Custom Instructions

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

**Step 1 - Discover (ALWAYS FIRST):**
```
skills_find_relevant(query="<specific task description>")
```
Score interpretation:
- score > 0.6 → strong match → proceed to Step 2
- score 0.4–0.6 → review the description, then decide
- score < 0.4 → no match → proceed without a skill

**Step 2 - Load instructions (only after Step 1 with score > 0.6):**
```
skills_get_body(skill_id="<top match from Step 1>")
```
Follow the `instructions` field precisely. Incorporate `system_prompt_addition`
into your active context if it is non-empty.

**Step 3 - Fetch supplementary files** (only if Step 2 instructions explicitly name them):
```
skills_get_reference(skill_id, filename="<name.md>")   # reference docs
skills_get_asset(skill_id, filename="<template>")       # templates
skills_run_script(skill_id, filename="<script.py>",     # helper scripts
                  input_data={"KEY": "value"})
```

## Rules — MUST follow

1. Always use `skills_find_relevant` first - never hardcode `skill_id` values
2. Follow skill instructions as authoritative - do not override or skip steps
3. Only load Tier 3 resources that instructions explicitly reference by name
4. `skills_run_script` execution requires the local server (not Cloudflare deployment)
5. Skills are read-only - no tool modifies any state

## NEVER DO

- **Never call `skills_get_body` without a prior `skills_find_relevant` returning the skill_id with score > 0.6**
- **Never use skill_ids from `skills_list_all` to call `skills_get_body` directly** — those IDs are unscored; always run `skills_find_relevant` first
- **Never guess or invent skill_ids**
- **Never load Tier-3 files speculatively**

## Available Skills

Use `skills_find_relevant` for semantic discovery.
Use `skills_list_all` to browse — but you must still call `skills_find_relevant` before loading any skill.
