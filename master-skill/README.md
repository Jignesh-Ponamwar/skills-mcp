# Skill MCP — Master Skill

Drop the right file into your project so your AI agent or coding tool
automatically knows how to discover and use the Skill MCP server.

---

## What's included

```
master-skill/
├── SKILL.md                         Universal skill definition (MCP-aware agents)
└── platforms/
    ├── antigravity/                 Google Antigravity IDE
    │   ├── AGENTS.md                Secondary cross-tool rules — drop in project root
    │   └── .agents/
    │       └── rules/
    │           └── GEMINI.md        Primary rules (highest priority) — drop .agents/ in project root
    ├── claude-code/
    │   └── CLAUDE.md                Claude Code — drop in project root
    ├── cursor/
    │   └── .cursorrules             Cursor — drop in project root
    ├── windsurf/
    │   └── .windsurfrules           Windsurf — drop in project root
    ├── codex/
    │   └── AGENTS.md                OpenAI Codex CLI — drop in project root
    ├── cline/
    │   └── .clinerules              Cline (VSCode) — drop in project root
    ├── copilot/
    │   └── .github/
    │       └── copilot-instructions.md  GitHub Copilot — drop .github/ in project root
    └── aider/
        └── CONVENTIONS.md           Aider — drop in project root
```

---

## Quick install

Pick the file for your tool and copy it into your project root:

### Claude Code
```bash
cp master-skill/platforms/claude-code/CLAUDE.md ./CLAUDE.md
```

### Cursor
```bash
cp master-skill/platforms/cursor/.cursorrules ./.cursorrules
```

### Windsurf
```bash
cp master-skill/platforms/windsurf/.windsurfrules ./.windsurfrules
```

### Cline (VSCode)
```bash
cp master-skill/platforms/cline/.clinerules ./.clinerules
```

### OpenAI Codex
```bash
cp master-skill/platforms/codex/AGENTS.md ./AGENTS.md
```

### GitHub Copilot
```bash
cp -r master-skill/platforms/copilot/.github ./.github
```

### Aider
```bash
cp master-skill/platforms/aider/CONVENTIONS.md ./CONVENTIONS.md
```

### Antigravity (Google)
```bash
# Primary rules file (highest priority — Antigravity reads this first)
cp -r master-skill/platforms/antigravity/.agents ./.agents

# Secondary cross-tool file (also read by Antigravity and Codex-compatible tools)
cp master-skill/platforms/antigravity/AGENTS.md ./AGENTS.md
```

---

## After copying

Edit the file and replace:
```
https://skill-mcp.<your-subdomain>.workers.dev/sse
```
with your actual deployed Worker URL (shown after `npx wrangler deploy`).

---

## How it works

Each file teaches the agent the **3-tier progressive disclosure workflow**:

1. **Tier 1 — Discover** (`skills_find_relevant`) — semantic search over the registry
2. **Tier 2 — Load** (`skills_get_body`, `skills_get_options`) — full instructions + manifest
3. **Tier 3 — Supplement** (`skills_get_reference`, `skills_run_script`, `skills_get_asset`) — load only what instructions reference

The agent learns when to check, how to interpret scores, and what to do with results.

---

## Adding to multiple projects

For teams using the same Skill MCP deployment, commit the relevant platform file
into each project repository. The agent will automatically follow the workflow
for every session in that project.

---

## SKILL.md — for MCP-aware agents

`SKILL.md` uses the same frontmatter format as the registry's own skills.
If your agent platform supports adding skills to the local skill directory,
add this file there to make the master workflow available as a retrievable skill:

```bash
# Example: add to skill_mcp skills_data for in-registry use
cp master-skill/SKILL.md skill_mcp/skills_data/skill-mcp-master/SKILL.md
```

Then re-run the seeder: `python -m skill_mcp.seed.seed_skills`
