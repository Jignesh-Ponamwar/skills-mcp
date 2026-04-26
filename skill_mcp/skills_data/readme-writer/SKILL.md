---
name: readme-writer
description: Create professional, comprehensive README.md files for software projects. Generates badges, installation instructions, usage examples, API references, and contributing guides tailored to the project type. Use when the user needs a README, wants to improve project documentation, or needs to write docs for a new repo.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [documentation, readme, markdown, open-source, developer-experience]
  platforms: [claude-code, cursor, any]
  triggers:
    - write a README
    - create README
    - improve my README
    - project documentation
    - write docs for this project
    - I need a README
    - document this repo
    - generate README.md
---

# README Writer Skill

## Overview
Generate professional README.md files that give developers everything they need to understand, install, and contribute to a project — in under 5 minutes of reading.

## Step-by-Step Process

### Step 1: Understand the Project
Before writing, gather:
- Project name and one-line description
- Primary language and tech stack
- Key features (3-5 bullet points)
- Target audience (library authors? end users? DevOps engineers?)
- License type
- Whether it has tests, CI, and a live demo

Read the project's entry point, package file (package.json, pyproject.toml, go.mod), and any existing docs.

### Step 2: Choose the Right README Template

**Library/SDK** — emphasize the API, installation, and quick start code
**CLI tool** — emphasize installation methods and command reference
**Web app/service** — emphasize features, screenshots, and deployment
**Data science / ML** — emphasize datasets, training steps, and results

### Step 3: Write the Header Section

```markdown
# Project Name

> One-line description of what this does and who it's for.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![CI](https://github.com/org/repo/actions/workflows/ci.yml/badge.svg)](...)
```

Badges to include (pick relevant):
- License
- Language version (Python, Node, Go)
- CI status
- npm/PyPI version (for published packages)
- Coverage (if configured)
- Docker pulls (if published)

### Step 4: Write Why It Exists (2-3 Paragraphs)
Explain the problem, the solution, and what makes this different. This is the most-skipped and most important section. Address: *why would I use this instead of X?*

### Step 5: Write Quick Start
```markdown
## Quick Start

\```bash
pip install mypackage
\```

\```python
from mypackage import Client
client = Client(api_key="...")
result = client.do_thing()
\```
```

The reader should be able to copy-paste and have something running in under 2 minutes.

### Step 6: Write Features Section
Use a bullet list. Be specific and concrete. Bad: "Fast". Good: "Processes 10k requests/sec on a t3.medium".

### Step 7: Write Installation Section
Include all supported methods:
- Package manager (pip, npm, brew, go get)
- From source (git clone + build steps)
- Docker (if applicable)
- Requirements / prerequisites

### Step 8: Write Configuration Reference
If the project takes config (env vars, config files, CLI flags), include a table:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | — | Your API key |
| `PORT` | No | 8000 | Server port |

### Step 9: Write API Reference (for Libraries)
Document the main public API with types and examples. Link to full API docs if they exist.

### Step 10: Write Contributing Section
```markdown
## Contributing
1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes and add tests
4. Open a PR against `main`

Run tests: `pytest` / `npm test` / `go test ./...`
```

### Step 11: Write License Section
```markdown
## License
Apache 2.0 — see [LICENSE](LICENSE).
```

## Quality Checklist
- [ ] No "TODO" placeholders left in the README
- [ ] All code examples are syntactically correct
- [ ] Badges link to real URLs
- [ ] Installation commands tested (or explicitly noted as untested)
- [ ] Contributing section explains how to run tests locally
- [ ] License section present

## Style Rules
- Use present tense: "This library **handles**..." not "This library **will handle**..."
- Lead with value: what it does, not how it's built
- No emoji unless the project's existing style uses them
- Keep the Quick Start under 20 lines — link to docs for the rest
