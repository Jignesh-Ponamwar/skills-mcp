# Skill MCP - Aider Conventions

This project uses a **Skill MCP server** - a registry of curated expert instructions
for common engineering tasks. Connect to it and follow skills when they apply.

## MCP Connection

```yaml
# Add to ~/.aider.conf.yml or project .aider.conf.yml:
mcp:
  skill-mcp:
    type: sse
    url: https://skill-mcp.<your-subdomain>.workers.dev/sse
```

## Conventions for Aider Sessions

### Always check for a skill first

At the start of any coding session involving non-trivial tasks, run:

```
/ask skills_find_relevant query="<specific description of the current task>"
```

Score thresholds:
- score > 0.6 → strong match → load it (Step 2)
- score 0.4–0.6 → review description, then decide
- score < 0.4 → no match → proceed without a skill

If score > 0.6, load the skill before writing any code:

```
/ask skills_get_body skill_id="<matched skill_id>"
```

### Skill-driven development workflow

1. **Discover** - `skills_find_relevant` with a specific query — ALWAYS FIRST
2. **Load** - `skills_get_body` for the best match (score > 0.6 only)
3. **Apply** - follow the `instructions` field exactly
4. **Supplement** - ONLY if instructions explicitly reference specific files:
   - `skills_get_reference` for reference docs
   - `skills_run_script` for helper scripts (local server only)
   - `skills_get_asset` for templates

### NEVER DO

- NEVER call `skills_get_body` without a prior `skills_find_relevant` returning the skill_id with score > 0.6
- NEVER use skill_ids from `skills_list_all` directly in `skills_get_body` — always run `skills_find_relevant` first to verify relevance
- NEVER guess or invent skill_ids
- NEVER load Tier-3 files speculatively

### Query examples

Good queries for skills_find_relevant:
- `"write pytest unit tests for SQLAlchemy async models"`
- `"review Python code for security vulnerabilities"`
- `"extract tables from multi-page PDF to CSV"`
- `"write conventional git commit message for staged changes"`

Poor queries: `"tests"`, `"code"`, `"help"`

### Code conventions (driven by skill instructions)

When a skill is loaded:
- Its `instructions` take precedence over default conventions
- Its `system_prompt_addition` extends the base context
- Templates from `skills_get_asset` should be used as file scaffolds

When no skill matches:
- Apply standard language-specific best practices
- Use existing project conventions

### Available skills

Use `skills_find_relevant` for discovery. Use `skills_list_all` to browse the full catalogue —
but after browsing you MUST still call `skills_find_relevant` before loading any skill.

*Do not hardcode skill_ids.*
