---
name: git-commit-writer
description: Generate standardised git commit messages following the Conventional Commits specification. Analyzes staged changes or diffs to produce atomic, descriptive commits. Use when the user wants to write a commit message, commit changes, follow conventional commits format, or generate git history.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [git, commits, conventional-commits, version-control]
  platforms: [claude-code, cursor, any]
  triggers:
    - write a commit message
    - commit this change
    - conventional commits
    - generate commit message
    - what should my commit say
    - git commit
    - squash commits
    - write git history
---

# Git Commit Writer Skill

## Overview
Generate precise, conventional commit messages from diffs or change descriptions. Follows the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) specification used by Angular, Vue, and thousands of open-source projects.

## Conventional Commits Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
| Type | When to use |
|------|------------|
| `feat` | New feature visible to users |
| `fix` | Bug fix |
| `docs` | Documentation only changes |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Code restructuring (no feature or fix) |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system, dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Other changes (e.g. updating `.gitignore`) |
| `revert` | Revert a previous commit |

### Breaking Changes
Add `!` after the type/scope, and a `BREAKING CHANGE:` footer:
```
feat(api)!: remove deprecated /v1/users endpoint

BREAKING CHANGE: The /v1/users endpoint has been removed. Use /v2/users instead.
```

## Step-by-Step Process

### Step 1: Understand the Change
Ask for or read the diff (`git diff --staged` or `git diff HEAD`). Understand:
- What changed (files, functions, logic)
- Why it changed (bug fix, new requirement, refactor)
- Whether it's a breaking change

### Step 2: Choose the Type
Apply the type that matches the *primary* intent. If a PR mixes types, flag it — atomic commits are better.

### Step 3: Choose the Scope (Optional)
Scope = the subsystem or module affected. Examples: `(auth)`, `(api)`, `(ui)`, `(db)`.
- Use it when the codebase has clear module boundaries
- Omit it for small or cross-cutting changes

### Step 4: Write the Description
Rules:
- Imperative mood: "add feature" not "added feature" or "adds feature"
- Lowercase first letter
- No period at the end
- Max 72 characters on the first line
- Describe WHAT, not HOW

Bad: `Fixed the bug with user login`
Good: `fix(auth): handle missing refresh token on session expiry`

### Step 5: Write the Body (When Needed)
Include a body when:
- The why is non-obvious
- There are multiple related changes
- A workaround or constraint is present

Separate from subject with a blank line. Wrap at 72 characters.

### Step 6: Add Footers
- `BREAKING CHANGE: <description>` — required for breaking changes
- `Closes #123` — closes a GitHub issue
- `Co-authored-by: Name <email>` — pair programming / AI assistance

## Examples

```
feat(payments): add Stripe webhook signature verification
```

```
fix(api): return 404 instead of 500 for unknown resource IDs

Previously the handler threw an unhandled KeyError when the resource
was not found, resulting in an opaque 500. Now returns a structured
404 with a message field.

Closes #847
```

```
refactor(db): replace raw SQL with SQLAlchemy ORM in user queries

No behavior changes. Preparatory step for the multi-tenant migration.
```

## Multi-commit Guidance
When the user has a large changeset that should be multiple commits:
1. Group changes by type and scope
2. Order: infrastructure → models → business logic → tests → docs
3. Each commit should pass tests in isolation
