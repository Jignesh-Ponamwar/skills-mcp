# Conventional Commit Examples

20 real-world commit messages covering all types, scopes, and edge cases. Use these as reference when generating commit messages.

---

## feat — New Features

```
feat(auth): add Google OAuth2 login provider
```

```
feat(api): implement cursor-based pagination for /users endpoint

Offset-based pagination caused inconsistent results when records were
inserted during iteration. Cursor-based pagination using created_at + id
compound cursor eliminates this race condition.

Closes #234
```

```
feat(dashboard): add real-time connection count widget

Uses WebSocket subscription to push counts every 5 seconds.
Falls back to 30-second polling if WebSocket is unavailable.
```

```
feat(search)!: replace fuzzy search with vector similarity search

BREAKING CHANGE: The ?q= parameter now performs semantic search using
sentence-transformers embeddings. The previous exact-match and prefix
behaviour is replaced. Clients relying on prefix matching should use
the new ?prefix= parameter instead.
```

```
feat(billing): add support for annual subscription discounts
```

---

## fix — Bug Fixes

```
fix(parser): handle empty array in JSON response without throwing
```

```
fix(auth): prevent session fixation by regenerating session ID on login

Previously the session ID was retained across the authentication boundary,
enabling session fixation attacks. Now generates a new session ID
immediately after successful credential verification.

Closes #789
```

```
fix(api): return 404 instead of 500 for missing resource IDs

Unhandled KeyError on unknown IDs produced an opaque 500 response.
Now catches the lookup failure and returns a structured 404.
```

```
fix(mailer): encode attachment filenames containing non-ASCII characters

RFC 2231 encoding required for filenames with spaces or non-Latin
characters. Previously caused Gmail to display garbled attachment names.
```

```
fix(cache): clear stale entries on key expiry rather than on next read

Stale entries were consuming memory until the next read triggered eviction.
Background cleanup now runs every 60 seconds via the scheduler.
```

---

## refactor — Code Restructuring

```
refactor(db): replace raw SQL with SQLAlchemy ORM in user queries

No behaviour changes. Preparatory step before the multi-tenant migration.
```

```
refactor(auth): extract token validation into standalone TokenValidator class

Decouples validation logic from the request handler, making it testable
in isolation and reusable across HTTP and WebSocket handlers.
```

```
refactor: split 800-line utils.py into focused modules

- string_utils.py: text manipulation helpers
- date_utils.py: timezone-aware date parsing
- crypto_utils.py: hashing and signing

No behaviour changes; all public names re-exported from utils.py
for backwards compatibility.
```

---

## docs, test, style, perf, build, ci, chore

```
docs(api): add rate limiting documentation to endpoint reference

Covers per-endpoint limits, headers returned, and retry guidance.
```

```
test(billing): add edge case tests for pro-rated subscription cancellation

Covers mid-cycle cancellation, cancellation on last day, and
cancellation when balance is negative.
```

```
style: apply Black formatting to entire codebase

Run: black --line-length 88 .
No logic changes.
```

```
perf(search): cache compiled regex patterns across requests

Previously recompiled on each request, causing ~2ms overhead per call.
Now compiled once at module load time.
```

```
build(deps): upgrade sentence-transformers from 2.7.0 to 3.0.1

3.0.1 includes the fix for the memory leak on repeated encode() calls
(upstream issue #2891). No API changes.
```

```
ci: add nightly security scan using pip-audit

Runs pip-audit on the pinned requirements and posts results to Slack.
Fails the nightly build on any new HIGH or CRITICAL CVEs.
```

```
chore: remove deprecated /v1/legacy endpoint stubs

These stubs have been no-ops since the v2 migration in Q1 2024.
Removing them to reduce cognitive overhead for new contributors.
```
