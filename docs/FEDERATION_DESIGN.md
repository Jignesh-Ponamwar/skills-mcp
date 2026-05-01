# Federation Design

**Status:** Architecture proposal — not yet implemented  
**Purpose:** Defines the long-term architecture for federated skill registries

---

## Why Federation

A single registry with 30–100 skills covers common tasks. At scale, this model breaks:

- **Scope conflict**: one public registry cannot serve both enterprise internal tooling and open-source community skills
- **Trust boundaries**: organizations want to control which skills their agents load — mixing public and private skills in one server blurs that boundary
- **Contributor incentives**: a single centralized registry creates a bottleneck and a single point of trust. A federated model allows organizations to run their own registries while still discovering public skills.
- **Resilience**: a single hosted instance is a single point of failure. Federated registries can fail independently.

The goal is not to replace the current single-registry model but to provide a clear upgrade path for organizations that need more control.

---

## The `skill://` URI Scheme

A `skill://` URI uniquely identifies a skill across registries:

```
skill://registry.host/skill-id@version
  │        │              │        │
  │        │              │        └── Version (optional, defaults to latest)
  │        │              └────────── Skill ID (slug)
  │        └───────────────────────── Registry hostname (authority)
  └────────────────────────────────── Scheme
```

Examples:

```
skill://skills-mcp.workers.dev/stripe-integration           # public registry, latest
skill://skills-mcp.workers.dev/stripe-integration@1.2       # public registry, pinned
skill://internal.acme.corp/acme-deploy-pipeline@2.0         # private enterprise registry
skill://localhost:8000/my-local-skill                       # local dev registry
```

The URI is already partially implemented — `SkillFrontMatter` has a `skill_uri` field in `skill_mcp/models/skill.py`. Currently it is set to an empty string. In a federated system, the seed script would populate it from the registry's base URL + skill ID + version.

---

## Registry Resolution Order

When an agent calls `skills_find_relevant`, the server performs resolution in this order:

1. **Local registry** — skills in the server's own Qdrant collections (always searched first)
2. **Trusted remote registries** — a configurable list of remote registry URLs (searched in order)
3. **Public fallback registry** — optional, can be disabled

Results from all registries are merged and ranked by score. The registry of origin is included in each result:

```json
{
  "skill_id": "stripe-integration",
  "skill_uri": "skill://skills-mcp.workers.dev/stripe-integration@1.2",
  "registry": "skills-mcp.workers.dev",
  "score": 0.87,
  "registry_type": "public"
}
```

Agents can be configured to restrict resolution to specific registries or registry types via a `registry_filter` parameter (future).

---

## Registry Types

### Public Registry

- Open to all, no authentication required
- Skills are community-contributed and publicly auditable
- Example: the current `skill-mcp` hosted instance

### Private Enterprise Registry

- Authentication required (Bearer token or mTLS)
- Skills are organization-internal and not publicly visible
- Can reference public skills by `skill_uri` (dependency declaration) without copying them
- Example: `internal.acme.corp` running a self-hosted skill-mcp instance

### Local Registry

- `localhost` or loopback address
- No authentication (trust-by-network)
- Used for development, testing, and air-gapped environments
- Example: Docker compose deployment

---

## Protocol Changes Required

### 1. Registry advertisement

Each registry exposes a `/.well-known/skill-registry.json` endpoint:

```json
{
  "version": "1.0",
  "registry_uri": "skill://skills-mcp.workers.dev",
  "name": "skill-mcp public registry",
  "trust_level": "public",
  "skills_count": 30,
  "embedding_model": "@cf/baai/bge-small-en-v1.5",
  "embedding_dim": 384,
  "contact": "https://github.com/Jignesh-Ponamwar/skills-mcp",
  "last_seeded": "2026-05-01T00:00:00Z"
}
```

This lets federation clients verify compatibility before connecting (embedding dimensions must match for cross-registry score comparison).

### 2. Federated search API

The `skills_find_relevant` tool gains a `registries` parameter:

```json
{
  "query": "set up Stripe webhooks",
  "top_k": 5,
  "registries": ["local", "skill://skills-mcp.workers.dev"]
}
```

Default: `["local"]` for self-hosted instances; `["local", "skill://skills-mcp.workers.dev"]` for deployments that opt into the public fallback.

The federation proxy logic lives in a new module: `skill_mcp/federation/proxy.py`.

### 3. Cross-registry skill dependencies

A skill can declare that it requires another skill from a different registry:

```yaml
metadata:
  dependencies:
    - skill://skills-mcp.workers.dev/docker-containerization@1.0
```

When an agent loads this skill, `skills_get_options` returns the dependencies and their source URIs. The agent can then fetch them via their respective registries. This is advisory — the agent decides whether to fetch dependencies, not the server.

---

## Storage Changes Required

### Qdrant

No schema changes to existing collections. Federation adds:

1. A `registry_uri` field to `skill_frontmatter` payloads (the origin registry of each skill)
2. Remote skills cached locally in Qdrant with a `cached_from_registry` flag and TTL
3. Optional: a `registry_metadata` collection storing the `/.well-known/skill-registry.json` payload for each configured remote registry

### Configuration

A new `registries.yml` configuration file (or environment variable `FEDERATION_REGISTRIES`):

```yaml
registries:
  - uri: "skill://internal.acme.corp"
    auth_token: "${INTERNAL_REGISTRY_TOKEN}"
    trust_level: "enterprise"
    cache_ttl_hours: 24

  - uri: "skill://skills-mcp.workers.dev"
    trust_level: "public"
    cache_ttl_hours: 6
    enabled: true
```

---

## Risk Analysis

### Score comparability across registries

Cross-registry score comparison only works if all registries use the same embedding model and dimension. If a remote registry uses a different model, its scores are not directly comparable to local scores. 

**Mitigation:** Registry advertisement includes `embedding_model` and `embedding_dim`. The federation proxy refuses to merge results from incompatible registries. Re-embedding remote skills locally is an option (expensive but accurate).

### Trust of remote skill content

When an agent loads a skill from a remote registry, the content bypasses the local prompt-injection scanner. An attacker who compromises a trusted remote registry can deliver malicious skill bodies.

**Mitigation:** 
- Local registries can be configured to re-scan cached remote skills
- Enterprise registries should maintain their own whitelist of trusted public skill URIs rather than enabling open federation

### Latency

Federated search multiplies latency by the number of registries searched in parallel. With 3 registries and 100ms per query, parallel federation adds ~100ms (not 300ms) but increases Qdrant load.

**Mitigation:** Local-first resolution with remote search only when no local skill scores > T_high. This keeps the fast path fast.

### Embedding model lock-in

The current model (`@cf/baai/bge-small-en-v1.5`) is specific to Cloudflare Workers AI. Federated deployments on non-Cloudflare infrastructure need an alternative embedding source.

**Mitigation:** Abstract the embedding provider behind an interface with multiple implementations:
- Cloudflare Workers AI (current default)
- OpenAI `text-embedding-3-small` (384-dim compatible if truncated)
- Local `sentence-transformers` model (no API dependency)

---

## Phased Migration from Current 3-Tier Model

### Phase 0 (current state)

Single registry, no federation. All skills in one Qdrant cluster. No `skill://` URIs populated.

### Phase 1 — URI foundation

- Populate `skill_uri` field in all existing skills: `skill://<configured-base-url>/<skill-id>@<version>`
- Add registry advertisement endpoint `/.well-known/skill-registry.json`
- No behavior change for existing deployments

**Backward compatibility:** complete. New fields are additive.

### Phase 2 — Local federation

- Add `registries.yml` configuration support
- Implement `federation/proxy.py` with parallel multi-registry search
- Add `registries` parameter to `skills_find_relevant`
- Default: `registries: ["local"]` — no behavior change unless explicitly configured

**Backward compatibility:** complete. New parameter is optional.

### Phase 3 — Remote skill caching

- Cache results from remote registries in local Qdrant with TTL
- Add `skills_refresh_cache(registry_uri)` admin tool
- Add cache staleness indicator to `skills_find_relevant` results for remote skills

**Backward compatibility:** additive. Cached remote skills appear alongside local ones.

### Phase 4 — Dependency resolution

- Support `dependencies` in `SkillOptions` with `skill://` URIs
- `skills_get_options` returns resolvable dependency URIs
- Master-skill files updated to include dependency-loading guidance

**Backward compatibility:** additive.

### Phase 5 — Enterprise auth and private registries

- mTLS and Bearer token support for registry connections
- Private registry skills are not included in public federation responses
- Admin tools for managing trusted registry list

**Backward compatibility:** new configuration surface, no breaking changes to existing API.

---

## Compatibility Notes

- **MCP protocol:** Federation is orthogonal to MCP transport. It works with both SSE and streamable-http.
- **Existing skill format:** No changes to `SKILL.md` format for Phases 1–3. Phase 4 adds an optional `dependencies` list to frontmatter.
- **Existing deployments:** All phases are additive. Operators who do not configure `registries.yml` see no behavior change.
- **The 3-tier progressive disclosure model** is preserved across federation. The only change is that skill results may originate from multiple registries rather than one.

---

## What is Not in Scope

This proposal does not cover:

- **Skill execution federation**: running `skills_run_script` on a remote registry's server. All execution remains local.
- **Skill publishing protocol**: a workflow for submitting skills to remote registries via API (vs. the current Git PR approach). This is a separate protocol design.
- **Real-time skill updates**: push-based notification from remote registries when a skill updates. Pull-based with TTL cache is sufficient for Phase 1–3.
- **Billing or quotas for remote registry access**: not in scope for open-source tooling.
