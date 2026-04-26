# Contributing to skill-mcp

Thank you for contributing. This document explains what this project is trying to become and where meaningful contributions can move it forward.

---

## What this project is really about

skill-mcp is an experiment in a specific idea: **that the boundary between a skill and an MCP server should dissolve**.

Right now the two are separate things — a skill is a markdown file an agent reads, an MCP server is infrastructure an agent calls. But the most useful version of this system would be one where the server *is* a skill. Where an agent connects to skill-mcp and the server itself teaches the agent how to use it, what to expect, when to search, how to interpret scores, and how to compose multiple skills into a coherent workflow — without the agent needing an external instruction file dropped in the project root.

That convergence is the real goal. The bundled SKILL.md files are a demo of the concept. The interesting open problems are architectural.

---

## Table of Contents

1. [Priority 1 — The server as a skill](#1-priority-1--the-server-as-a-skill)
2. [Priority 2 — MCP tool design](#2-priority-2--mcp-tool-design)
3. [Priority 3 — Agent efficiency](#3-priority-3--agent-efficiency)
4. [Priority 4 — Protocol and infrastructure](#4-priority-4--protocol-and-infrastructure)
5. [Skill format reference](#5-skill-format-reference)
6. [Validation and CI](#6-validation-and-ci)
7. [Security policy](#7-security-policy)
8. [Review process](#8-review-process)
9. [The two invariants](#9-the-two-invariants)

---

## 1. Priority 1 — The server as a skill

The current approach to teaching agents the 3-tier workflow is a drop-in file: `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, etc. — one per platform, installed manually. This works but it's fragile. The instruction file can be missing, stale, or ignored.

The better version: **the server describes itself through the protocol**. An agent that connects to skill-mcp and calls `tools/list` should receive tool descriptions that are precise enough to tell the agent exactly when to call each tool, in what order, and how to interpret the responses — without any external file.

### Open problems in this space

**Tool description quality.** MCP tool descriptions are the primary interface between the server and the agent's decision-making. Today's descriptions are functional but not optimally instructive. A good tool description doesn't just say what the tool does — it tells the agent the *precondition* for calling it, the *postcondition* it should expect, and the *decision rule* for what to do next.

Example of a description that guides behavior rather than just documenting it:

```
skills_find_relevant(query, top_k=5)

ALWAYS call this first before attempting any technical task. Returns skills ranked
by semantic similarity. Use the score to decide next action:
  score > 0.6  → call skills_get_body() immediately
  score 0.4–0.6 → read the description field and decide
  score < 0.4  → no match, proceed without a skill
Do not call skills_get_body() before calling this tool.
```

**A self-description tool.** Consider a `skills_describe_protocol()` tool (or resource) that returns the full 3-tier workflow as structured data — the decision tree, score thresholds, tier-3 loading rules — in a format optimised for agent comprehension, not human reading.

**Structured response envelopes.** Right now tool responses are plain text or JSON blobs. Responses could include a `next_action` hint — a machine-readable field that explicitly tells the agent what to do with the result rather than leaving it to inference:

```json
{
  "results": [...],
  "next_action": {
    "if_score_above": 0.6,
    "call": "skills_get_body",
    "with": { "skill_id": "stripe-integration" }
  }
}
```

**Contributions here:** tool description rewrites, new self-description tools or resources, response envelope design, experiments measuring whether specific description changes improve agent behavior.

---

## 2. Priority 2 — MCP tool design

The current 6 tools (find, get_body, get_options, get_reference, run_script, get_asset) cover the happy path. There are real gaps.

### Tools worth designing

**`skills_list_all()`** — returns all skill IDs with their one-line descriptions. Semantic search is the right entrypoint for most tasks, but agents sometimes benefit from knowing the full catalogue — especially when the task is ambiguous or when they suspect a skill exists but their query isn't matching. This is a cheap Qdrant scroll, not an embedding call.

**`skills_suggest_workflow(task)`** — given a multi-step task description, returns an ordered list of skills that together cover the full workflow. Example: "build and deploy a FastAPI app with auth" might suggest `[fastapi, docker-containerization, github-actions]` in sequence. This requires either LLM reasoning in the Worker (possible via a CF AI text model) or a simpler graph of skill dependencies declared in the options collection.

**`skills_get_manifest(skill_id)`** — returns the tier3_manifest without loading the full body. Useful when an agent has already loaded the body in a previous turn and only needs to know what supplementary files are available.

**`skills_find_batch(queries)`** — submit multiple queries in a single call and get back results for all of them. Agents working on compound tasks often know upfront that they need several skills. Today they make N round trips; this collapses it to one.

**`skills_refresh_hint(skill_id)`** — given that a skill body was loaded N turns ago, return a short refresher (the first section or a summary) without reloading the full body. Helps agents that have scrolled past the instructions in long conversations.

### Tool design principles

A tool that an agent will use correctly is designed around how agents reason, not around what is technically convenient to implement.

- **Preconditions in the description** — state when the tool should NOT be called as clearly as when it should
- **Postconditions that guide the next step** — the description should tell the agent what to do with the result
- **Errors that teach** — error responses should explain what the agent did wrong and what to do instead, not just return a status code
- **No ambiguous optional parameters** — if a parameter is optional but almost always needed, make that explicit in the description

**Contributions here:** designing and implementing new tools, improving existing tool descriptions, adding structured `next_action` response fields, writing tests that verify agent behavior against specific tool interactions.

---

## 3. Priority 3 — Agent efficiency

The 3-tier model is sound in theory. In practice, agents skip the skill lookup, call `skills_get_body` without first calling `skills_find_relevant`, or load skills they don't need. Understanding why this happens and fixing it is more valuable than adding more skills.

### Open problems in this space

**Measuring agent compliance.** There is currently no instrumentation for whether agents are actually following the intended workflow. Adding structured logging to the Worker — recording which tools were called in what order per session — would make it possible to identify where the protocol breaks down.

**Master-skill effectiveness.** The platform-specific instruction files (`CLAUDE.md`, `.cursorrules`, etc.) teach the workflow. But there's no data on which formulations actually work. Different platforms interpret instructions differently. Testing specific phrasings against real agent sessions and measuring compliance would produce genuinely useful results.

**Score threshold calibration.** The 0.6 strong / 0.4 review thresholds were set by judgment, not measurement. For a given embedding model and skill corpus, there's a distribution of match scores. The thresholds should be derived from that distribution — the right cutoff is wherever precision and recall trade off best for the actual use case. This requires building an evaluation set of (query, expected_skill) pairs and running it.

**Multi-skill composition.** Most non-trivial tasks require more than one skill. The current model has no way to express that "after loading skill A, also check skill B." Options: skill-level dependency declarations in the options collection, a workflow graph, or letting the agent discover composition through `skills_find_relevant` at each step. The right answer is unknown and worth exploring.

**Session continuity.** A skill body loaded in turn 3 of a conversation may no longer be in the agent's effective context window by turn 15. The server has no way to know this. Ideas: conversation turn counters in the MCP session, proactive reload hints returned by other tools, or skill bodies that include explicit "checkpoint" reminders designed to be re-referenced.

**Contributions here:** instrumentation and logging, master-skill evaluation frameworks, evaluation datasets for threshold calibration, multi-skill workflow design, session continuity experiments.

---

## 4. Priority 4 — Protocol and infrastructure

### Transport

The Worker currently uses the MCP SSE transport (GET `/sse` + POST `/messages/`). The MCP spec now defines `streamable-http` as the preferred transport. Migrating the Worker to streamable-http would simplify the protocol and remove the dependency on maintaining an SSE connection per session.

### Federation

A single skill-mcp instance with 30–100 skills covers most use cases. But organizations may want multiple registries — one for internal tooling, one for public skills, one per team. Design questions: how does an agent discover which registry to query first? Can a registry proxy queries to other registries? Can skills declare cross-registry dependencies?

### Embedding model flexibility

The system is currently coupled to `@cf/baai/bge-small-en-v1.5` (384-dim). The model is embedded in both the seed script (via REST) and the Worker (via AI binding). Decoupling model configuration from the code — so operators can choose a different embedding model without forking — would make the system more adaptable. The main constraint is that seed-time and query-time must use the same model.

### Collection schema evolution

As skills gain new fields (e.g., `confidence_scores`, `dependencies`, `last_verified`), the Qdrant collection schemas need to evolve. There's currently no migration system — re-seeding overwrites. A proper migration layer that handles schema changes without requiring a full re-seed would be valuable for production deployments.

### Security scanner improvements

The prompt-injection scanner (`skill_mcp/security/prompt_injection.py`) uses regex pattern matching. The known gap is semantic attacks — injection phrased in ways that evade pattern matching but are understood by LLMs. Two directions worth exploring:

- **LLM-assisted review**: calling a Claude API endpoint during CI to ask "does this skill body contain prompt injection attempts?" — expensive but more accurate for edge cases
- **Adversarial test corpus**: building a dataset of known-injection and known-clean skill bodies to measure scanner precision/recall over time

**Contributions here:** streamable-http transport migration, federation protocol design, embedding model abstraction, collection migration tooling, LLM-assisted scanner, adversarial test corpus.

---

## 5. Skill format reference

Skills are part of the project and PRs that add or improve them are welcome. But skills are not the primary contribution surface. Prefer contributions that improve how agents interact with the system over contributions that add content to it.

If you do add a skill, these are the rules.

### Directory structure

```
skill_mcp/skills_data/
└── my-skill-slug/
    ├── SKILL.md          ← required
    ├── references/       ← optional: markdown reference docs
    ├── scripts/          ← optional: executable scripts (.py, .js, .ts, .sh)
    └── assets/           ← optional: templates and static output formats
```

### SKILL.md format

```markdown
---
name: my-skill-slug
description: >
  Written from the agent's perspective: "Use when the user asks to [task].
  Covers [scope]. Do NOT use for [out-of-scope things]."
license: Apache-2.0
metadata:
  author: your-github-username
  version: "1.0"
  tags: [tag1, tag2]
  platforms: [claude-code, cursor, any]
  triggers:
    - natural language phrase an agent would use when searching
    - another distinct phrasing of the same intent
    - at least 3, ideally 5–10
---

# Skill Title

Step-by-step instructions. This is what the agent reads and executes.

## Common Mistakes

What agents get wrong without this skill. Be specific.

## References

- For full API reference, see `references/API.md`
- To scaffold the project, run `scripts/scaffold.py`
```

### Critical rules

**Only `description + triggers` are embedded.** Write them to match how an agent would phrase the need — not how you'd name the skill. The body is never embedded and can be as detailed as needed.

**Reference tier-3 files by name in the body.** The agent receives a `tier3_manifest` and fetches only files explicitly mentioned in the instructions. Nothing loads speculatively.

**`name` must match the directory slug exactly.**

### Validation before PR

```bash
# Schema + injection scan
python scripts/validate_skills.py skill_mcp/skills_data/my-skill/SKILL.md

# All skills (make sure nothing regresses)
python scripts/validate_skills.py
```

---

## 6. Validation and CI

Every PR that touches `skills_data/` runs three CI jobs automatically:

| Job | What it checks |
|-----|---------------|
| **yaml-lint** | All SKILL.md frontmatter parses as valid YAML |
| **check-duplicates** | No duplicate slugs or names |
| **validate-skills** | Schema + prompt-injection scan on changed files; posts a summary comment |

**Common YAML mistake:** `@` at the start of an unquoted string is invalid YAML. Quote it:
```yaml
triggers:
  - "@anthropic-ai/sdk"   # ✅ correct
  - @anthropic-ai/sdk     # ❌ YAML error
```

For code contributions (not skills), CI runs `pytest`. All 40 prompt-injection scanner tests must pass.

---

## 7. Security policy

Skills load directly into agent context windows. All submitted skills are scanned before merge. See [`THREAT_MODEL.md`](THREAT_MODEL.md) for the full threat model.

**CRITICAL/HIGH findings block merge:** instruction-override phrases, role hijacking, prompt delimiter injection (`</system>`, `[INST]`), credential exfiltration patterns, HTML injection outside code blocks, Unicode BiDi attacks, base64 payloads that decode to injection content.

**False positive?** Open an issue with the skill file and scanner output. Do not bypass or disable the scanner.

**Scanner bypass?** Disclose privately — do not open a public issue. This is a real attack surface.

---

## 8. Review process

**Response time:** 3–5 business days.

**What shifts a PR from good to great:**
- For tool/protocol changes: evidence that the change improves agent behavior, not just that it's technically correct
- For infrastructure changes: benchmarks or measurements that justify the tradeoff
- For skill additions: demonstration of a specific failure mode the skill prevents

**What will get a PR closed without merge:**
- Skills that are documentation paraphrases without added procedural value
- Tool additions that don't come with a clear agent behavior story
- Changes that break the two invariants

---

## 9. The two invariants

These two rules must never be broken regardless of the change:

**Invariant 1: Never embed the full body.**

Only `description + triggers` go into the `skill_frontmatter` vector collection. The body is payload-only. Embedding the body pollutes the search space with instruction prose — the search space should contain only intent signals, not instructions.

**Invariant 2: Never return script source to the agent.**

`skills_run_script` returns `stdout`, `stderr`, and `exit_code` only. The script source is stored server-side and executed server-side. It is never returned. This is a security boundary, not a convenience choice.

---

## Starting point

The highest-leverage place to start is reading `src/worker.py` (the MCP tool implementations) and the `master-skill/` instruction files side by side. The gap between what the tool descriptions say and what the master-skill files have to add manually to make agents behave correctly — that gap is the most productive thing to close.

Open a [Discussion](https://github.com/Jignesh-Ponamwar/skills-mcp/discussions) before starting large changes. Design alignment before implementation avoids wasted work.
