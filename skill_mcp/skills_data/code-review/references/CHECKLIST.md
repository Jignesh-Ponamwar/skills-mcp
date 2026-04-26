# Code Review Checklist

Structured checklists for security, performance, correctness, and style reviews. Use as a systematic scan before writing findings.

---

## Security Checklist

### Injection (OWASP A03)
- [ ] SQL queries use parameterized statements / ORM — never string concatenation
- [ ] Shell commands use argument lists (`subprocess.run(["cmd", arg])`) — never `shell=True` with user input
- [ ] Template rendering uses auto-escaping — no `|safe` or `Markup()` on user data
- [ ] XML/HTML parsers use defusedxml or equivalent — no `lxml.etree.fromstring` on untrusted input
- [ ] LDAP queries use attribute-value escaping

### Authentication & Secrets (OWASP A02, A07)
- [ ] No hardcoded API keys, passwords, or tokens in source code
- [ ] No secrets in comments, log statements, or error messages
- [ ] Passwords hashed with bcrypt / argon2 / scrypt — not MD5, SHA1, or SHA256 alone
- [ ] JWT secrets are sufficiently random (≥32 bytes entropy)
- [ ] Session tokens are invalidated on logout
- [ ] Password reset tokens are single-use and expire within 1 hour

### Cryptography (OWASP A02)
- [ ] No use of ECB mode for block ciphers
- [ ] No use of RC4, DES, or 3DES
- [ ] RSA keys ≥ 2048 bits; EC curves ≥ P-256
- [ ] IV/nonce is random per message — not hardcoded or sequential
- [ ] MAC authentication before decryption (encrypt-then-MAC)

### Access Control (OWASP A01)
- [ ] Every endpoint checks that the authenticated user owns the requested resource (anti-IDOR)
- [ ] Admin endpoints require explicit role check — not just authentication
- [ ] File downloads validate the path against a whitelist — no `../` traversal
- [ ] Server-side redirects validate destination against allowlist (anti-open redirect)

### Input Validation (OWASP A03, A04)
- [ ] All user inputs validated for type, range, and format server-side
- [ ] File uploads: type validated by magic bytes — not just extension
- [ ] File uploads: stored outside web root with random names
- [ ] URL parameters decoded before validation (double-encoding attacks)

### Dependency Security (OWASP A06)
- [ ] No known CVEs in direct dependencies (check with `pip audit` / `npm audit`)
- [ ] Pinned versions in production — no `>=` wildcard for security-sensitive packages
- [ ] Removed unused dependencies

---

## Performance Checklist

### Database
- [ ] No N+1 queries — check for queries inside loops
- [ ] Indexes exist for all foreign keys and frequently-filtered columns
- [ ] `SELECT *` replaced with explicit column list in hot paths
- [ ] Large result sets use pagination (`LIMIT`/`OFFSET` or cursor-based)
- [ ] Mutations in a tight loop are batched (bulk insert / update)
- [ ] Long-running transactions release locks promptly

### Application
- [ ] Heavy computations cached (result memoized or stored)
- [ ] Synchronous blocking I/O not called from an async event loop
- [ ] Large files streamed — not loaded entirely into memory
- [ ] Regular expressions pre-compiled with `re.compile()` outside the hot loop
- [ ] Unnecessary object copies avoided in inner loops

### API / Network
- [ ] External API calls have timeouts configured
- [ ] Retries use exponential backoff with jitter
- [ ] Responses cached where safe (ETags, `Cache-Control`)
- [ ] HTTP connection pooling used — not creating new connections per request

---

## Correctness Checklist

### Error Handling
- [ ] No bare `except:` or `except Exception: pass`
- [ ] All exceptions are logged before being swallowed
- [ ] Error messages do not expose stack traces or internal paths to end users
- [ ] Transient errors (network, DB timeouts) are retried before failing

### Data Types
- [ ] Integer division vs float division — no accidental truncation
- [ ] Off-by-one in slice/index operations
- [ ] Null/None propagation — operations on nullable fields guarded
- [ ] Date/time zones: stored in UTC, converted at display layer only
- [ ] Decimal used for currency — not float

### Concurrency
- [ ] Shared mutable state protected by locks where applicable
- [ ] No race conditions in read-modify-write sequences
- [ ] Async code uses `asyncio.Lock` — not threading locks

---

## Style Checklist

### Naming
- [ ] Variables and functions named for what they ARE, not what they DO transiently
- [ ] Boolean variables/functions use `is_`, `has_`, `can_` prefix
- [ ] Constants are UPPER_SNAKE_CASE
- [ ] No single-letter variables except loop counters (`i`, `j`) and well-known conventions (`x`, `y`)

### Maintainability
- [ ] No magic numbers — named constants used
- [ ] Functions ≤ ~50 lines (flag for discussion, not mandate)
- [ ] No deeply nested conditionals (>3 levels) — extract helpers
- [ ] Dead code removed (commented-out blocks, unreachable branches)
- [ ] TODO/FIXME comments have an owner and tracking reference

### Documentation
- [ ] Public functions have docstrings with parameter types and return description
- [ ] Complex algorithms have inline comments explaining WHY, not WHAT
- [ ] README updated if public API or deployment steps changed

---

## Finding Severity Guide

| Severity | Criteria | Action |
|----------|----------|--------|
| CRITICAL | RCE, auth bypass, data exfiltration, secret exposure | Block merge, fix immediately |
| HIGH | XSS, SQLi, IDOR, data corruption, crash in prod | Fix before merge |
| MEDIUM | Logic bug affecting some users, weak crypto | Fix in this PR or create tracked issue |
| LOW | Style violation, suboptimal code, minor perf | Fix opportunistically or defer |
| INFO | Alternative approach worth considering | Discuss, no action required |
