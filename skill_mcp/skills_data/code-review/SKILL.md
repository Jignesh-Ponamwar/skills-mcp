---
name: code-review
description: Review code for correctness, bugs, security vulnerabilities, performance issues, and best practices. Produces structured findings with severity ratings and concrete fixes. Use when the user asks to review code, check for bugs, find security issues, audit code quality, or get a second opinion on an implementation.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [code-review, security, quality, bugs, best-practices]
  platforms: [claude-code, cursor, any]
  triggers:
    - review this code
    - check my code
    - find bugs
    - code review
    - audit this implementation
    - is this code correct
    - security review
    - check for vulnerabilities
    - improve this code
    - what's wrong with this
---

# Code Review Skill

## Overview
A structured, language-agnostic code review process that identifies bugs, security issues, performance problems, and style violations. Always produces actionable output with severity ratings.

## Review Process

### Step 1: Read Before Commenting
Read the entire code block before writing any feedback. Understanding the full context prevents false positives and surface-level comments.

### Step 2: Identify the Language and Context
Note the language, framework, and apparent purpose. Calibrate expectations accordingly (e.g., prototype vs. production, CLI script vs. library).

### Step 3: Check for Correctness
- Logic errors and off-by-one bugs
- Unhandled edge cases (null/None, empty collections, negative numbers)
- Incorrect operator precedence or type coercion
- Missing error handling at I/O boundaries
- Race conditions in concurrent code

### Step 4: Check for Security Issues
Scan specifically for:
- **Injection**: SQL injection, shell injection, SSTI, XSS
- **Hardcoded secrets**: API keys, passwords, tokens in source
- **Insecure deserialization**: `pickle.loads`, `eval`, `exec` on user input
- **Path traversal**: user-controlled file paths without sanitization
- **Weak cryptography**: MD5/SHA1 for passwords, ECB mode, short keys
- **IDOR**: direct object references without authorization checks
- **SSRF**: user-controlled URLs in outbound HTTP requests

### Step 5: Check for Performance Issues
- N+1 query patterns (database calls inside loops)
- Unnecessary copying of large data structures
- Missing indexes on frequently-queried fields
- Blocking I/O on async event loops
- Redundant computations that could be cached

### Step 6: Check for Maintainability
- Unclear variable or function names
- Functions longer than ~50 lines (flag, don't mandate splitting)
- Missing or incorrect type annotations (for typed languages)
- Magic numbers without named constants
- Dead code or unused imports

### Step 7: Write Structured Findings

Use this format for each finding:
```
[SEVERITY] Category: Title
File: path/to/file.py, Line: N
Issue: One sentence describing the problem.
Impact: What could go wrong.
Fix:
  <corrected code snippet>
```

Severity levels:
- **CRITICAL**: Data loss, RCE, auth bypass, secret exposure
- **HIGH**: Security vulnerability, data corruption, crash in production
- **MEDIUM**: Logic bug, incorrect behavior in edge cases
- **LOW**: Style, naming, missing docs, minor inefficiency
- **INFO**: Suggestion or alternative approach

### Step 8: Provide a Summary

End with:
- Overall assessment (1-2 sentences)
- Count of findings by severity
- Top 3 priority fixes

## Rules
- Only flag real issues — don't rewrite working code to apply style preferences
- Cite exact line numbers when possible
- Explain WHY each issue matters, not just what it is
- For security findings, show the attack scenario
- Provide corrected code for CRITICAL/HIGH findings; optional for LOW/INFO
