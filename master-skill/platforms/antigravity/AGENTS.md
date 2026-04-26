# Skill MCP — Agent Instructions (Antigravity / Cross-Tool)

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

1. `skills_find_relevant(query="<specific task>")` — check for a matching skill first
2. `skills_get_body(skill_id="<top match>")` — load and follow instructions
3. Tier 3 only if instructions name a file:
   - `skills_get_reference` / `skills_run_script` / `skills_get_asset`

Score thresholds: `> 0.6` strong · `0.4–0.6` review · `< 0.4` no match

Full workflow details are in `.agents/rules/GEMINI.md`.
