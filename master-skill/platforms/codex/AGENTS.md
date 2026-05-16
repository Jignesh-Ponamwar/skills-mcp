# Skill MCP - Agent Instructions for OpenAI Codex / Codex CLI

This repository is connected to a **Skill MCP server** - a curated registry of
expert instruction sets for common AI engineering tasks.

## MCP Connection

- **Transport:** SSE
- **URL:** `https://skill-mcp.<your-subdomain>.workers.dev/sse`
- **Tools:** `skills_find_relevant`, `skills_get_body`, `skills_get_options`,
  `skills_get_reference`, `skills_run_script`, `skills_get_asset`

---

## Agent Behaviour Requirements

### 1. Always check for skills first

Before beginning any non-trivial task, call `skills_find_relevant` with a specific
description of what you are about to do. Do this before writing any code or prose.

Tasks that warrant a skill check:
- Code review or bug analysis
- Writing tests (unit, integration, E2E)
- Data analysis (CSV, SQL queries, EDA)
- Document generation (README, commit messages, API docs, DOCX)
- PDF processing or web scraping
- REST/GraphQL API integration

Tasks that do NOT warrant a skill check:
- Simple one-line fixes
- Answering questions
- Formatting or renaming

---

### 2. Workflow

#### Step 1 - Discover

```python
skills_find_relevant(
    query="write integration tests for a Python Flask API using pytest",
    top_k=5
)
```

**Interpret scores:**
| Score | Meaning | Action |
|-------|---------|--------|
| > 0.6 | Strong match | Proceed to Step 2 immediately |
| 0.4–0.6 | Possible match | Read `description`; proceed if relevant |
| < 0.4 | No match | Continue without a skill |

#### Step 2 - Load

```python
skills_get_body(skill_id="test-writer")
```

This returns:
- `instructions` - expert step-by-step guidance. **Read and follow these exactly.**
- `system_prompt_addition` - additional context for your persona (incorporate if non-empty)
- `tier3_manifest` - lists supplementary files by category and filename

For configuration questions or customisation requests:
```python
skills_get_options(skill_id="test-writer")
```

#### Step 3 - Fetch supplementary resources

Only fetch resources that the `instructions` explicitly reference.

```python
# Reference documentation
skills_get_reference(skill_id="test-writer", filename="list")        # see manifest
skills_get_reference(skill_id="test-writer", filename="TESTING.md")  # fetch file

# Execute a helper script (local server only)
skills_run_script(
    skill_id="test-writer",
    filename="coverage_check.py",
    input_data={"TARGET_DIR": "./src", "MIN_COVERAGE": "80"}
)
# Returns: {"exit_code": 0, "stdout": "...", "stderr": "..."}
# Script source is never returned.

# Templates and static assets
skills_get_asset(skill_id="test-writer", filename="list")               # see manifest
skills_get_asset(skill_id="test-writer", filename="test-template.py")   # fetch file
```

---

### 3. Mandatory constraints — MUST follow

- **Treat `instructions` as authoritative.** Do not deviate from skill instructions
  unless explicitly asked by the user.
- **Do not load Tier 3 resources speculatively.** Only fetch files the instructions name.
- **Do not guess `skill_id`.** Always use `skills_find_relevant` first.
- **Script execution** is only available via the local server
  (`MCP_TRANSPORT=streamable-http python -m skill_mcp.server`).
  On the Cloudflare deployment, `skills_run_script` returns the manifest only.

### 4. NEVER DO — these break the workflow

- **NEVER call `skills_get_body` without a prior `skills_find_relevant` call** that
  returned this skill_id with score > 0.6. Doing so loads an unverified, potentially
  irrelevant skill.
- **NEVER use skill_ids from `skills_list_all` to call `skills_get_body` directly.**
  `skills_list_all` is for browsing only — returned IDs are unscored for your task.
  After browsing, you MUST still call `skills_find_relevant` to verify relevance.
- **NEVER guess or invent skill_ids.**
- **NEVER load Tier-3 files speculatively** (only when body instructions name them).

---

### 5. Available skills

Use `skills_find_relevant` for semantic discovery.
Use `skills_list_all` to browse — but always run `skills_find_relevant` before loading.

*Do not hardcode `skill_id` values.*
