# Skill Reviewer Checklist

This checklist is for maintainers reviewing PRs that add or modify skills. It is also public — contributors should read it before submitting so they can pre-address every item.

Use this as a rubric, not a mechanical pass/fail gate. Each section has a severity label: **Block** (must be resolved before merge), **Resolve** (needs discussion or clarification), or **Note** (log but do not block).

---

## 1. Schema and Format — Block

- [ ] `name` in frontmatter exactly matches the directory slug
- [ ] `description` is present and at least one complete sentence
- [ ] `metadata.triggers` has at least 3 entries
- [ ] `metadata.version` follows `"MAJOR.MINOR"` format (e.g. `"1.0"`)
- [ ] `metadata.author` is present (GitHub username or name)
- [ ] `license` is set to `Apache-2.0` (or contributor has explicitly agreed to a compatible license)
- [ ] Frontmatter YAML parses without error (`python scripts/validate_skills.py`)

---

## 2. Prompt-Injection Scan — Block

- [ ] Scanner returns `CLEAN` or `WARNED` (not `BLOCKED`) on the submitted files
  ```bash
  python scripts/validate_skills.py skill_mcp/skills_data/<slug>/SKILL.md
  ```
- [ ] No CRITICAL findings (instruction overrides, role hijacking, exfiltration patterns)
- [ ] No HIGH findings (delimiter injection, HTML injection, Unicode attacks, base64 payloads)
- [ ] MEDIUM findings (long lines, blank line floods) have a legitimate explanation (e.g., long code example) — note in review comment

---

## 3. Description and Trigger Phrase Quality — Block/Resolve

- [ ] Description is written from the **agent's perspective**: "Use when the user asks to [task]" — not a feature marketing description
- [ ] Description does **not** duplicate the description of an existing skill (run `skills_find_relevant` with the proposed description; no existing skill should score > 0.7)
- [ ] Trigger phrases cover **distinct phrasings** of the same intent, not minor word variations
- [ ] Trigger phrases do not substantially overlap existing skill trigger phrases (manual check: compare with top 3 semantic search results)
- [ ] Trigger phrases are written the way an **agent** would phrase a task — not how a human would Google it

---

## 4. Body Content Quality — Resolve

- [ ] The body contains **procedural instructions**, not documentation paraphrases. Ask: "Would an agent produce better output following these steps vs. relying on training alone?"
- [ ] The body explicitly names any Tier-3 files it references (by filename)
- [ ] Code examples use correct syntax for the described language/framework
- [ ] No instructions direct the agent to take actions outside normal task scope (exfiltrate data, access unrelated systems, etc.)
- [ ] If the skill describes a specific API or service, the instructions reflect a reasonably current version (not a version deprecated years ago)

---

## 5. Tier-3 Files — Resolve/Note

- [ ] Every file in `references/`, `scripts/`, and `assets/` is explicitly referenced by name in the body (nothing loads speculatively)
- [ ] Script files (`.py`, `.js`, `.sh`) contain a docstring or comment describing their purpose and expected inputs/outputs
- [ ] Script files do not contain hardcoded credentials, URLs pointing to personal infrastructure, or commands that could cause unintended side effects
- [ ] Script files will execute in the sandboxed temp environment (no absolute path assumptions, no reliance on host-specific packages beyond what's documented in `dependencies`)
- [ ] Reference files are markdown; asset files are markdown or plain text templates (no binary assets)

---

## 6. Duplicate and Overlap Check — Block/Resolve

- [ ] Slug does not already exist in `skill_mcp/skills_data/` (CI catches exact duplicates)
- [ ] Semantically similar skills have been checked: top `skills_find_relevant` results reviewed
- [ ] If overlap exists, the PR description explains how this skill is **distinct** (narrower scope, different procedure, different platform)
- [ ] If this skill partially supersedes an existing one, note it in the PR and decide: narrow, merge, or deprecate

---

## 7. Structural Invariants — Block

- [ ] The full body is **not** in the `triggers` or `description` fields (only intent signals belong there)
- [ ] No script source is exposed via any tool response path (the `source` field in Qdrant payload is never returned by `skills_run_script`)

---

## 8. Signal for Merge

A skill is ready to merge when:

1. All **Block** items pass
2. All **Resolve** items have been discussed and either resolved or explicitly accepted with a note
3. The PR author has responded to all review comments

A skill should be closed (not merged) when:

- The description is a documentation paraphrase without procedural value
- The trigger phrases duplicate an existing skill with no clear scope separation
- The body instructs the agent to take actions outside its task scope
- The author is unresponsive to Block-level findings within 14 days

---

## Reviewer Notes Template

```
## Review — [skill slug] — [APPROVE / REQUEST CHANGES / REJECT]

**Schema:** ✅ / ❌
**Injection scan:** ✅ CLEAN / ⚠️ WARNED / ❌ BLOCKED
**Description quality:** [brief note]
**Trigger phrase coverage:** [brief note]
**Overlap check:** [results of skills_find_relevant + decision]
**Body content:** [procedural value assessment]
**Tier-3 files:** ✅ / N/A / [issues found]
**Invariants:** ✅

**Decision:** [APPROVE / REQUEST CHANGES: <specific items> / REJECT: <reason>]
```
