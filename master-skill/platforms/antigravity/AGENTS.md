# Skill MCP - Agent Instructions (Antigravity / Cross-Tool)

This file is read by Antigravity IDE as a secondary rules source alongside
`.agents/rules/GEMINI.md`. It is also compatible with OpenAI Codex CLI and
other tools that follow the `AGENTS.md` convention.

For Antigravity-specific configuration (higher priority), see:
`.agents/rules/GEMINI.md`

---

## MCP Server

- **Transport:** SSE
- **URL:** `https://skill-mcp.<your-subdomain>.workers.dev/sse`

## Skill Workflow (summary)

1. `skills_find_relevant(query="<specific task>")` — ALWAYS FIRST, no exceptions
2. `skills_get_body(skill_id="<top match>")` — ONLY if score > 0.6 from Step 1
3. Tier 3 ONLY if body instructions explicitly name a file:
   - `skills_get_reference` / `skills_run_script` / `skills_get_asset`

Score thresholds: `> 0.6` strong → load · `0.4–0.6` review description · `< 0.4` no match

**NEVER** call `skills_get_body` with a skill_id not returned by `skills_find_relevant` with score > 0.6.
**NEVER** use skill_ids from `skills_list_all` directly — always run `skills_find_relevant` first.

Full workflow details are in `.agents/rules/GEMINI.md`.
