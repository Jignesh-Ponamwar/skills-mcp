# Conventional Commits 1.0.0 — Full Reference

Complete specification for the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard used as the basis for the git-commit-writer skill.

---

## Specification

A commit message MUST conform to this structure:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Required Elements

**type** — Must be one of the registered types below. All lowercase.

**description** — A short summary of the change:
- Written in imperative, present tense: "add feature" not "added feature"
- First letter lowercase
- No period at the end
- Maximum 72 characters on the first line (subject line including type and scope)

### Optional Elements

**scope** — Parenthesised noun describing the section of the codebase changed:
- `feat(parser):` `fix(api):` `refactor(auth):`
- Must be lowercase
- No spaces inside parens
- Omit if the change is cross-cutting

**body** — Free-form additional context:
- Separated from subject by exactly one blank line
- Wrap lines at 72 characters
- Explain WHY, not WHAT (the diff shows what)

**footer(s)** — Key-value pairs at the end:
- Separated from body (or subject if no body) by exactly one blank line
- Format: `Token: value` or `Token #number`
- Multiple footers each on their own line

---

## Commit Types

### Core Types

| Type | Purpose | Triggers SemVer |
|------|---------|-----------------|
| `feat` | New feature visible to users | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation changes only | — |
| `style` | Formatting, whitespace — no behavior change | — |
| `refactor` | Code restructuring — no feature or fix | — |
| `perf` | Performance improvement | PATCH |
| `test` | Adding or correcting tests | — |
| `build` | Build system, dependency updates | — |
| `ci` | CI/CD configuration changes | — |
| `chore` | Catch-all for tooling, scripts, gitignore | — |
| `revert` | Reverts a previous commit | — |

### Breaking Changes

Breaking changes can appear in ANY type. Two ways to mark them:

**Method 1 — `!` suffix (preferred for prominence):**
```
feat(api)!: remove deprecated /v1/users endpoint
```

**Method 2 — `BREAKING CHANGE:` footer:**
```
feat(api): migrate user endpoint to v2

BREAKING CHANGE: The /v1/users endpoint has been removed.
Use /v2/users with the updated request schema instead.
```

Both methods are valid; they can be combined. `BREAKING CHANGE` in a footer ALWAYS triggers a MAJOR version bump regardless of type.

---

## Special Footers

### `BREAKING CHANGE`
Required when a commit introduces an incompatible API change.
```
BREAKING CHANGE: password field renamed from `pass` to `password_hash`
```

### `Closes` / `Fixes` / `Resolves`
Links to issue tracker items. Multiple allowed.
```
Closes #123
Fixes #456
```

### `Co-authored-by`
For pair programming or AI assistance.
```
Co-authored-by: Alice Smith <alice@example.com>
Co-authored-by: Claude Sonnet <noreply@anthropic.com>
```

### `Reviewed-by`
```
Reviewed-by: Bob Jones <bob@example.com>
```

---

## SemVer Mapping

| Commit content | SemVer bump |
|---------------|------------|
| `BREAKING CHANGE` footer or `!` | MAJOR (1.x.x → 2.0.0) |
| `feat:` or `feat(...):` | MINOR (1.2.x → 1.3.0) |
| `fix:`, `perf:` | PATCH (1.2.3 → 1.2.4) |
| Everything else | No version bump |

---

## Validation Rules

1. First line (subject) ≤ 72 characters
2. Type is lowercase and from the registered list
3. Description is lowercase (first word)
4. No period at end of description
5. Body and footers separated by blank lines
6. `BREAKING CHANGE` footer must be followed by a description
7. Footer tokens use `: ` or ` #` as separator (no space before colon)

---

## Parser Regex (for tooling)

The official commit message regex:

```
^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?(!)?: .+
```

Full message with optional breaking change detection:
```python
import re

COMMIT_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^()]+)\))?"
    r"(?P<breaking>!)?"
    r": (?P<description>.+)"
    r"(?:\n\n(?P<body>[\s\S]*?))?"
    r"(?:\n\n(?P<footer>[\s\S]*))?$"
)
```

---

## Examples by Scenario

### Simple patch
```
fix(auth): correct token expiry calculation off-by-one error
```

### New feature with scope and body
```
feat(payments): add Stripe webhook signature verification

Incoming webhooks were previously accepted without signature
verification, making the endpoint vulnerable to spoofed events.
Now validates using HMAC-SHA256 with the STRIPE_WEBHOOK_SECRET.
```

### Breaking change with body and footer
```
feat(api)!: require API version header on all requests

The X-API-Version header is now required for all API calls.
Requests without this header receive a 400 Bad Request response.
This enables parallel support for v1 and v2 clients during migration.

BREAKING CHANGE: Clients must send X-API-Version: 2 header.
Closes #892
```

### Revert
```
revert: feat(auth): add OAuth2 provider support

Reverts commit abc1234.

This OAuth2 implementation had unresolved token refresh race conditions.
Revisit after the session management refactor lands.
```
