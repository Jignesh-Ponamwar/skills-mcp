# Skill MCP — Aider Conventions

This project uses a **Skill MCP server** — a registry of curated expert instructions
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

If a skill matches (score > 0.4), load it before writing any code:

```
/ask skills_get_body skill_id="<matched skill_id>"
```

### Skill-driven development workflow

1. **Discover** — `skills_find_relevant` with a specific query
2. **Load** — `skills_get_body` for the best match
3. **Apply** — follow the `instructions` field exactly
4. **Supplement** — only if instructions reference specific files:
   - `skills_get_reference` for reference docs
   - `skills_run_script` for helper scripts (local server only)
   - `skills_get_asset` for templates

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

api-integration, code-review, data-analysis, docx-creator, git-commit-writer,
pdf-processing, readme-writer, sql-query-writer, test-writer, web-scraper

*Use `skills_find_relevant` for discovery — do not hardcode skill_ids.*
