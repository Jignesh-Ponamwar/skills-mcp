# Skill Versioning Design

**Status:** Implemented  
**Implemented in:** `skill_mcp/models/skill.py`, `skill_mcp/db/qdrant_manager.py`, `skill_mcp/seed/seed_skills.py`, `skill_mcp/tools/get_skill_body.py`, `skill_mcp/server.py`, `src/worker.py`

---

## Problem Statement

Skills currently have no versioning beyond a decorative `metadata.version: "1.0"` field in `SKILL.md` frontmatter. When a skill is re-seeded, the previous payload is overwritten with no record of what changed. Agents always receive the latest version with no ability to pin to a known-good state.

This creates several problems:

1. **Silent regressions** — a skill update can change agent behavior in all active deployments immediately, with no visibility
2. **No rollback** — if a seeded skill has a bug, recovery requires editing and re-seeding from git history
3. **No drift detection** — agents cannot detect that a skill they loaded in turn 3 has since changed
4. **No explicit deprecation** — skills cannot signal "use `new-skill` instead of `old-skill`"

---

## Versioning Scheme

Skills use **semantic versioning** with two components:

```
MAJOR.MINOR
  │     └── Backwards-compatible additions (new trigger phrases, expanded body, new Tier-3 files)
  └──────── Breaking changes (scope change, removed functionality, incompatible trigger phrases)
```

`PATCH` is omitted because skill bodies are prose, not code — the line between a "patch" and a "minor" change is too ambiguous to be useful.

Examples:
- `1.0` → `1.1`: Added two trigger phrases, expanded the "Common Mistakes" section
- `1.1` → `2.0`: Rewrote the skill for a new API version (old instructions still work but are now outdated)

---

## How Versioning Works at Each Layer

### 1. SKILL.md frontmatter

No change required to the existing format. The `version` field is already present:

```yaml
metadata:
  version: "1.2"
```

Version is a string (not semver object) to avoid YAML parsing complexity. The seed script parses it.

### 2. Qdrant storage

Currently, skills are stored with a deterministic point ID derived from `skill_id`. Re-seeding overwrites the previous payload.

**Proposed change:** point IDs become `skill_id@version` keys. Both the current and previous versions are kept until explicitly pruned.

```
skill_frontmatter collection:
  point_id: uuid5("stripe-integration@1.0")  ← old version, payload includes version="1.0"
  point_id: uuid5("stripe-integration@1.1")  ← new version, payload includes version="1.1"
  point_id: uuid5("stripe-integration")      ← "latest" alias, always same content as newest
```

The `latest` alias point is always overwritten by re-seeding, so agents that do not pin always get the newest version. Pinned agents use `skill_id@version` notation.

### 3. MCP tool interface

The `skills_get_body` and `skills_find_relevant` tools gain an optional `version` parameter:

```
skills_get_body(skill_id="stripe-integration")           # latest
skills_get_body(skill_id="stripe-integration", version="1.0")  # pinned
```

The short form `skill_id="stripe-integration@1.0"` is also accepted and parsed server-side — this allows master-skill files to reference specific versions without changing the tool signature.

**Fallback:** if `version` is specified but not found, the tool returns the latest version with a `version_note` field: `"Requested version 1.0 not found; returning latest (1.2)"`.

### 4. Frontmatter search results

`skills_find_relevant` returns a `version` field in each result:

```json
{
  "skill_id": "stripe-integration",
  "version": "1.2",
  "description": "...",
  "score": 0.87
}
```

If the caller needs to pin: they read the version from the discovery result and use it in subsequent `skills_get_body` calls.

---

## Changelog / Deprecation Flow

### Adding a changelog

Each `SKILL.md` body should include a `## Changelog` section at the bottom (not embedded, not affecting the embedding):

```markdown
## Changelog

- **1.2** (2026-05-01): Updated Stripe webhooks section for API version 2024-06-20; added idempotency key pattern
- **1.1** (2026-03-15): Added Stripe Connect (Accounts v2) section
- **1.0** (2026-01-10): Initial version
```

### Deprecating a skill

A deprecated skill adds `deprecated: true` to frontmatter and a `replaced_by` field:

```yaml
metadata:
  deprecated: true
  replaced_by: "stripe-integration-v2"
```

`skills_find_relevant` returns deprecated skills in results but appends a `deprecated` flag. The master skill files instruct agents to prefer non-deprecated matches. `skills_get_body` on a deprecated skill returns the body with a `deprecation_notice` field.

---

## Version Pruning

Old versions accumulate in Qdrant unless explicitly pruned. The seed script will gain a `--prune-old-versions` flag that removes all non-latest version points older than a configurable threshold (default: 90 days).

This is a maintenance operation, not automatic. Operators running production deployments should prune periodically via `make seed-prune` (planned target).

---

## Drift Detection

Agents that loaded a skill in an earlier turn have no way to know if the skill was updated. Two partial mitigations:

1. **Version in body response:** `skills_get_body` returns a `version` field in the response envelope. Agents that log or record this can detect drift by comparing to a fresh `skills_find_relevant` result.
2. **Session timestamps (future):** If the Worker gains session tracking, it could embed a `loaded_at` timestamp in the body response and expose a `skills_check_freshness(skill_id, loaded_version)` tool that returns `"current"` or `"stale: loaded 1.1, current is 1.2"`.

---

## Migration Plan

The versioning system is backward-compatible. The migration sequence:

1. **Phase A** — add `version` field to all existing skills in `SKILL.md` (already present, set to `"1.0"`)
2. **Phase B** — update seed script to store `skill_id@version` point IDs alongside `skill_id` latest alias
3. **Phase C** — add optional `version` parameter to `skills_get_body` and `skills_find_relevant` in both `src/worker.py` and `skill_mcp/tools/`
4. **Phase D** — update master-skill files to mention version pinning in the 3-tier workflow description
5. **Phase E** — add `make seed-prune` target for old version cleanup

Phases A and B can land independently. Phase C requires both worker and local server updates in the same PR.

---

## Open Questions

- **How many historical versions to keep by default?** Proposal: keep 2 (current + previous). Simple, cheap, enough for rollback.
- **Should `skills_find_relevant` search across all versions or only `latest`?** Proposal: search only `latest` by default. Version-pinned search (`version="1.0"`) searches that specific version's frontmatter vector.
- **Should the version be part of the `skill_uri`?** The `skill://` URI scheme (see [FEDERATION_DESIGN.md](FEDERATION_DESIGN.md)) should include version: `skill://registry.host/stripe-integration@1.2`.

---

## Implementation Status

- ✅ `skill_mcp/models/skill.py`: `deprecated: bool` and `replaced_by: str` added to `SkillFrontMatter` and `SkillRecord`
- ✅ `skill_mcp/db/qdrant_manager.py`: `get_body_versioned(skill_id, version)` and `get_frontmatter_payload(skill_id)` methods; `version_key` keyword index on body collection; `upsert_many_frontmatter` / `upsert_many_body` write both latest alias and versioned points
- ✅ `skill_mcp/tools/get_skill_body.py`: accepts `version` parameter and inline `@version` suffix; falls back to latest with `version_note`; attaches `deprecation_notice` when deprecated
- ✅ `skill_mcp/server.py`: tool registration passes `version=version`
- ✅ `src/worker.py`: identical version pinning, inline suffix, and deprecation notice in the Worker
- ⏳ CI: version format validation in `validate-skills` workflow (not yet added)
- ⏳ `Makefile`: `seed-prune` target for removing old version points (not yet added)
