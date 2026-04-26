# Code Review — Structured Output Template

Copy this template and fill in each section for the code being reviewed.

---

## Review Summary

**Date:** {date}
**Reviewer:** AI Code Review
**Language / Framework:** {language_and_framework}
**Files reviewed:** {file_list}
**Lines of code:** {loc}

**Overall assessment:**
{1-2 sentence summary of the overall code quality and key concerns}

**Finding counts:**

| Severity | Count |
|----------|-------|
| CRITICAL | {n} |
| HIGH | {n} |
| MEDIUM | {n} |
| LOW | {n} |
| INFO | {n} |

**Top 3 priority fixes:**
1. {highest_priority_fix}
2. {second_priority_fix}
3. {third_priority_fix}

---

## Findings

### [CRITICAL] {Title} *(Line {N})*

**Category:** {security | bug | data-loss | ...}
**CWE:** {CWE-ID if security finding, else N/A}

**Issue:**
{One paragraph describing what is wrong and where exactly.}

**Attack scenario / Impact:**
{How this could be exploited or what goes wrong in production.}

**Remediation:**
```{language}
{corrected code snippet}
```

---

### [HIGH] {Title} *(Line {N})*

**Category:** {category}

**Issue:**
{Description.}

**Impact:**
{Impact description.}

**Remediation:**
```{language}
{fix}
```

---

### [MEDIUM] {Title} *(Line {N})*

**Category:** {category}

**Issue:**
{Description.}

**Remediation:**
```{language}
{fix}
```

---

### [LOW] {Title} *(Line {N})*

**Category:** {category}

**Issue:**
{Description.}

**Suggestion:**
```{language}
{suggestion}
```

---

### [INFO] {Title}

{Alternative approach or observation. No action required.}

---

## Positive Notes

- {Something the author did well — always include at least one}
- {Another positive observation}

---

## Follow-up Recommended

- [ ] {Action item with owner if known}
- [ ] Run `{tool}` in CI to catch {category} issues automatically
