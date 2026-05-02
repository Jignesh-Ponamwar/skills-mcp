"""
Cloudflare Workers entry point for skill-mcp.

Two MCP transports — both active simultaneously:

  Legacy SSE (MCP spec 2024-11-05) — Claude Desktop, Claude.ai, Cursor, etc.
    GET  /sse          — open SSE stream; server sends messages endpoint URL
    POST /messages/    — receive JSON-RPC message; response sent via SSE stream

  Streamable HTTP (MCP spec 2025-03-26) — Glama, new SDK clients
    POST /mcp          — stateless JSON-RPC request→response
    OPTIONS *          — CORS preflight (204 + CORS headers)

CORS headers are included on every response so browser-based testers work.

Bindings (wrangler.jsonc + `wrangler secret put`):
  AI             — Workers AI (@cf/baai/bge-small-en-v1.5, 384-dim)
  QDRANT_URL     — secret: Qdrant Cloud cluster URL
  QDRANT_API_KEY — secret: Qdrant Cloud API key
  MCP_OBJECT     — Durable Object (holds ASGI app + SSE session state)

Optional env vars:
  RATE_LIMIT_RPM — per-IP rate limit in requests/min (default: 60)
"""

from __future__ import annotations

import asyncio
import js  # Pyodide JS bridge — always available in Cloudflare Python Workers
import json
import time
import urllib.parse
import uuid
from typing import Any

from workers import DurableObject


# ── HTTP helpers via js.fetch (urllib TCP sockets are NOT supported in Workers) ─
#
# Cloudflare Workers runs Python inside a Pyodide/WebAssembly sandbox that does
# NOT permit raw TCP connections.  urllib.request.urlopen silently hangs or times
# out.  All outbound HTTP must go through the JS `fetch` global instead.


async def _js_fetch(
    url: str,
    method: str,
    headers: dict[str, str],
    body: str | None = None,
) -> dict:
    """Async HTTP call via js.fetch. Returns parsed JSON. Raises RuntimeError on errors.

    Error messages deliberately omit the full URL and raw response body to avoid
    leaking internal cluster addresses, API keys embedded in auth headers, or
    detailed Qdrant error messages back to MCP clients.
    """
    init: dict[str, Any] = {"method": method, "headers": headers}
    if body is not None:
        init["body"] = body
    # js.JSON.parse creates a real JS plain object (not a Map) so fetch accepts it
    js_init = js.JSON.parse(json.dumps(init))
    try:
        response = await js.fetch(url, js_init)
        text = await response.text()
    except Exception as exc:
        # Don't include the URL — it may contain cluster-specific host info
        raise RuntimeError(f"Upstream request failed: {exc}") from exc
    if not response.ok:
        # Include only the HTTP status; omit URL and response body which may
        # contain internal paths, stack traces, or cluster configuration details.
        raise RuntimeError(f"Upstream returned HTTP {response.status}")
    return json.loads(text)


# ── Qdrant REST helpers ────────────────────────────────────────────────────────


async def _qdrant(
    qdrant_url: str,
    api_key: str,
    path: str,
    body: dict | None = None,
    method: str = "POST",
) -> dict:
    """Single Qdrant REST call via js.fetch. Raises RuntimeError on HTTP errors."""
    url = f"{qdrant_url.rstrip('/')}{path}"
    return await _js_fetch(
        url,
        method=method,
        headers={"Content-Type": "application/json", "api-key": api_key},
        body=json.dumps(body) if body is not None else None,
    )


async def _search(
    qdrant_url: str, api_key: str, collection: str, vector: list[float], limit: int
) -> list[dict]:
    result = await _qdrant(
        qdrant_url,
        api_key,
        f"/collections/{collection}/points/search",
        {"vector": vector, "limit": limit, "with_payload": True},
    )
    return result.get("result", [])


async def _scroll(
    qdrant_url: str, api_key: str, collection: str, filter_: dict, limit: int = 100
) -> list[dict]:
    result = await _qdrant(
        qdrant_url,
        api_key,
        f"/collections/{collection}/points/scroll",
        {"filter": filter_, "limit": limit, "with_payload": True},
    )
    return [p["payload"] for p in result.get("result", {}).get("points", [])]


def _by_skill(skill_id: str) -> dict:
    return {"must": [{"key": "skill_id", "match": {"value": skill_id}}]}


def _by_skill_file(skill_id: str, filename: str) -> dict:
    return {
        "must": [
            {"key": "skill_id", "match": {"value": skill_id}},
            {"key": "filename", "match": {"value": filename}},
        ]
    }


def _by_version_key(version_key: str) -> dict:
    """Filter for a specific versioned body point, e.g. 'stripe-integration@1.2'."""
    return {"must": [{"key": "version_key", "match": {"value": version_key}}]}


# ── MCP tool schemas (returned by tools/list) ─────────────────────────────────

_MCP_TOOLS: list[dict] = [
    {
        "name": "skills_find_relevant",
        "description": (
            "STEP 1 — Discover relevant skills. Call this FIRST at the start of any task "
            "to check whether the registry contains a curated skill that matches. "
            "Performs semantic vector search and returns ranked results with similarity scores.\n\n"
            "Workflow after this call:\n"
            "  • score > 0.6  → strong match — call skills_get_body with that skill_id\n"
            "  • score 0.4–0.6 → possible match — inspect description before proceeding\n"
            "  • score < 0.4  → no relevant skill — proceed without one\n\n"
            "Query tips: be task-specific, not generic. "
            "'write pytest unit tests for a Flask REST API' outperforms 'testing'. "
            "Describe what you are trying to accomplish, not what you want to find."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural-language description of the current task. "
                        "Be specific — include language, framework, and goal."
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of ranked results to return (1–20, default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "skills_get_body",
        "description": (
            "STEP 2 — Load full skill instructions. Call after skills_find_relevant "
            "once you have identified the best-matching skill_id.\n\n"
            "Returns three fields:\n"
            "  • instructions         — expert step-by-step guidance; read and follow these\n"
            "  • system_prompt_addition — optional context to add to your persona (may be empty)\n"
            "  • tier3_manifest       — lists available references, scripts, and assets by filename\n\n"
            "After loading: apply the instructions. "
            "If tier3_manifest lists files that the instructions explicitly reference, "
            "fetch them with skills_get_reference, skills_run_script, or skills_get_asset. "
            "Most tasks are fully served by the instructions alone — do not load Tier 3 speculatively.\n\n"
            "Version pinning: pass version='1.2' to pin to a specific skill version, or use the "
            "inline form skill_id='stripe-integration@1.2'. If the requested version is not found, "
            "the latest version is returned with a version_note explaining the fallback. "
            "Deprecated skills include a deprecation_notice field naming the replacement."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": (
                        "skill_id from skills_find_relevant. "
                        "May include an inline version suffix: 'stripe-integration@1.2'"
                    ),
                },
                "version": {
                    "type": "string",
                    "description": "Optional version string (e.g. '1.2') to pin to a specific skill version.",
                },
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "skills_get_options",
        "description": (
            "OPTIONAL STEP 2b — Load config schema, variants, and constraints for a skill. "
            "Call only when: (a) the user asks to customize skill behaviour, or "
            "(b) skills_get_body instructions mention configurable options.\n\n"
            "Returns: config_schema (JSON Schema for parameters), "
            "variants (alternative skill modes), "
            "dependencies (required tools/packages), "
            "limitations (known constraints).\n\n"
            "Do NOT call this by default — most tasks complete with skills_get_body alone."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "skills_get_reference",
        "description": (
            "STEP 3a — Fetch a reference document bundled with a skill "
            "(markdown files: checklists, policies, API specs, examples).\n\n"
            "Two-phase use:\n"
            "  1. Call with filename='list' (default) to see the full reference manifest\n"
            "  2. Call again with the specific filename to fetch its content\n\n"
            "Only call when: tier3_manifest from skills_get_body lists reference files "
            "AND the skill instructions explicitly name one. "
            "Do not load references speculatively."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "filename": {
                    "type": "string",
                    "description": "Exact filename to fetch (e.g. 'CHECKLIST.md'), or 'list' for manifest",
                    "default": "list",
                },
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "skills_run_script",
        "description": (
            "STEP 3b — Execute a helper script bundled with a skill. "
            "Script source is NEVER returned — only stdout, stderr, and exit_code.\n\n"
            "Two-phase use:\n"
            "  1. Call with filename='list' to see available scripts and their descriptions\n"
            "  2. Call with the specific filename (and optional input_data) to execute\n\n"
            "input_data: key-value pairs passed to the script as environment variables.\n\n"
            "Deployment note: script execution requires the local server "
            "(MCP_TRANSPORT=streamable-http python -m skill_mcp.server). "
            "The Cloudflare Workers deployment returns the manifest only — "
            "Pyodide has no subprocess support.\n\n"
            "Only call when skill instructions direct you to run a specific script."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "filename": {
                    "type": "string",
                    "description": "Script filename, or 'list' for manifest (default)",
                    "default": "list",
                },
                "input_data": {
                    "type": "object",
                    "description": "Input values (not used in Workers deployment)",
                },
                "list_only": {
                    "type": "boolean",
                    "description": "Always return the script manifest",
                    "default": False,
                },
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "skills_get_asset",
        "description": (
            "STEP 3c — Fetch a template or static resource bundled with a skill "
            "(markdown templates, config starters, example data files).\n\n"
            "Two-phase use:\n"
            "  1. Call with filename='list' (default) to see the full asset manifest\n"
            "  2. Call again with the specific filename to fetch its content\n\n"
            "Use the returned content as a starting template — adapt it to the specific task. "
            "Only call when skill instructions reference a specific asset file."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "filename": {
                    "type": "string",
                    "description": "Exact asset filename to fetch (e.g. 'report-template.md'), or 'list' for manifest",
                    "default": "list",
                },
            },
            "required": ["skill_id"],
        },
    },
]


# ── ASGI app factory ───────────────────────────────────────────────────────────


def _build_server(env: Any):
    """
    Return a bare ASGI callable implementing both MCP transports.
    No third-party packages required — pure stdlib.

    Routes:
      OPTIONS *        — CORS preflight (204)
      GET  /sse        — legacy SSE transport: open stream, send endpoint event
      POST /messages/  — legacy SSE transport: receive JSON-RPC, route to stream
      POST /mcp        — Streamable HTTP: stateless JSON-RPC request→response
    """

    # Active SSE sessions: session_id → asyncio.Queue of outbound JSON-RPC dicts.
    # Lives in this closure, which is held by the DO instance.
    _sessions: dict[str, asyncio.Queue] = {}

    # ── Per-IP rate limiting ───────────────────────────────────────────────────
    _RATE_LIMIT: int = int(getattr(env, "RATE_LIMIT_RPM", None) or 60)
    _RATE_WINDOW: float = 60.0
    _rate_store: dict[str, list[float]] = {}

    def _check_rate_limit(ip: str) -> bool:
        now = time.time()
        cutoff = now - _RATE_WINDOW
        timestamps = _rate_store.get(ip, [])
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= _RATE_LIMIT:
            _rate_store[ip] = timestamps
            return False
        timestamps.append(now)
        _rate_store[ip] = timestamps
        # Evict stale IPs when store grows beyond 10k entries
        if len(_rate_store) > 10_000:
            stale_cutoff = now - _RATE_WINDOW * 2
            stale = [k for k, v in _rate_store.items() if not v or max(v) < stale_cutoff]
            for k in stale:
                del _rate_store[k]
        return True

    def _client_ip(scope: dict) -> str:
        headers = dict(scope.get("headers", []))
        return (
            headers.get(b"cf-connecting-ip", b"").decode()
            or headers.get(b"x-forwarded-for", b"unknown").decode().split(",")[0].strip()
        )

    C_FM = "skill_frontmatter"
    C_BODY = "skill_body"
    C_OPTS = "skill_options"
    C_REFS = "skill_references"
    C_SCRIPTS = "skill_scripts"
    C_ASSETS = "skill_assets"

    def _creds() -> tuple[str, str]:
        return getattr(env, "QDRANT_URL", ""), getattr(env, "QDRANT_API_KEY", "")

    _EMBED_MODEL = "@cf/baai/bge-small-en-v1.5"

    async def _embed(query: str) -> list[float]:
        """Return a 384-dim embedding vector for *query*.

        Strategy (tried in order):
          1. Workers AI binding with js.JSON.parse() input — avoids the Python
             dict → JS Map conversion that causes AiError 5006.
          2. Workers AI binding with js.eval() literal — alternative JS object form.
          3. Workers AI REST API via urllib — works if WORKERS_AI_ACCOUNT_ID and
             WORKERS_AI_API_TOKEN secrets are set; zero extra dependencies.

        Raises RuntimeError if all three strategies fail.
        """
        payload_json = json.dumps({"text": str(query)})
        binding_err: str = ""

        # ── Strategy 1 & 2: Workers AI binding ────────────────────────────────
        for js_input_fn, label in [
            (lambda: js.JSON.parse(payload_json), "js.JSON.parse"),
            (lambda: js.eval(f"({{text: {json.dumps(str(query))}}})"), "js.eval"),
        ]:
            try:
                js_inputs = js_input_fn()
                ai_raw = await env.AI.run(_EMBED_MODEL, js_inputs)
                # Convert JsProxy → Python
                if hasattr(ai_raw, "to_py"):
                    ai_py = ai_raw.to_py()
                    return list(ai_py["data"][0])
                # Attribute-access fallback for non-to_py JsProxy
                data_p = getattr(ai_raw, "data", None)
                if data_p is not None:
                    row = data_p.to_py()[0] if hasattr(data_p, "to_py") else data_p[0]
                    return list(row)
                return list(ai_raw["data"][0])  # type: ignore[index]
            except Exception as exc:
                binding_err = f"{label}: {exc}"
                continue  # try next strategy

        # ── Strategy 3: REST API fallback via js.fetch ────────────────────────
        acct_id: str = getattr(env, "WORKERS_AI_ACCOUNT_ID", "")
        ai_token: str = getattr(env, "WORKERS_AI_API_TOKEN", "")
        if acct_id and ai_token:
            url = (
                f"https://api.cloudflare.com/client/v4/accounts/{acct_id}"
                f"/ai/run/{_EMBED_MODEL}"
            )
            try:
                rest_result = await _js_fetch(
                    url,
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {ai_token}",
                        "Content-Type": "application/json",
                    },
                    body=payload_json,
                )
                if not rest_result.get("success"):
                    errs = rest_result.get("errors") or []
                    msg = "; ".join(str(e.get("message", e)) for e in errs) or "unknown"
                    raise RuntimeError(f"REST API returned failure: {msg}")
                return list(rest_result["result"]["data"][0])
            except Exception as rest_exc:
                raise RuntimeError(
                    f"All embedding strategies failed. "
                    f"Binding error: {binding_err}. "
                    f"REST error: {rest_exc}"
                ) from rest_exc

        raise RuntimeError(
            f"Workers AI binding failed ({binding_err}). "
            "Set WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN secrets "
            "to enable the REST API fallback."
        )

    # ── Tool implementations ───────────────────────────────────────────────────

    async def _skills_find_relevant(query: str, top_k: int = 5) -> str:
        if not str(query).strip():
            return json.dumps({"error": "query is required"})
        QU, QK = _creds()

        vector: list[float] = await _embed(query)
        hits = await _search(QU, QK, C_FM, vector, int(top_k))
        skills = [
            {
                "skill_id": h["payload"].get("skill_id"),
                "name": h["payload"].get("name"),
                "description": h["payload"].get("description"),
                "tags": h["payload"].get("tags", []),
                "platforms": h["payload"].get("platforms", []),
                "trigger_phrases": h["payload"].get("trigger_phrases", []),
                "skill_uri": h["payload"].get("skill_uri"),
                "score": h.get("score"),
            }
            for h in hits
        ]
        return json.dumps(
            {"query": query, "total_found": len(skills), "results": skills}, indent=2
        )

    async def _skills_get_body(skill_id: str, version: str | None = None) -> str:
        QU, QK = _creds()

        # Parse inline version suffix: "stripe-integration@1.2"
        if "@" in skill_id and version is None:
            skill_id, version = skill_id.rsplit("@", 1)

        version_note: str | None = None

        if version:
            # Try pinned version point first
            ver_key = f"{skill_id}@{version}"
            payloads = await _scroll(QU, QK, C_BODY, _by_version_key(ver_key), 1)
            if not payloads:
                # Fall back to latest with a note
                payloads = await _scroll(QU, QK, C_BODY, _by_skill(skill_id), 1)
                if payloads:
                    version_note = (
                        f"Requested version {version!r} not found in registry; "
                        f"returning latest version."
                    )
        else:
            payloads = await _scroll(QU, QK, C_BODY, _by_skill(skill_id), 1)

        if not payloads:
            return json.dumps(
                {"error": f"skill_id '{skill_id}' not found in body collection"}
            )
        body = payloads[0]

        # Attach version_note if version was requested but not found
        if version_note:
            body = {**body, "version_note": version_note}

        # Attach deprecation notice from frontmatter if deprecated
        fm_payloads = await _scroll(QU, QK, C_FM, _by_skill(skill_id), 1)
        if fm_payloads and fm_payloads[0].get("deprecated"):
            replaced_by = fm_payloads[0].get("replaced_by", "")
            msg = "This skill is deprecated."
            if replaced_by:
                msg += f" Use '{replaced_by}' instead."
            body = {**body, "deprecation_notice": msg}
        refs = sorted(
            p.get("filename", "")
            for p in await _scroll(QU, QK, C_REFS, _by_skill(skill_id))
            if p.get("filename")
        )
        scripts = sorted(
            p.get("filename", "")
            for p in await _scroll(QU, QK, C_SCRIPTS, _by_skill(skill_id))
            if p.get("filename")
        )
        assets = sorted(
            p.get("filename", "")
            for p in await _scroll(QU, QK, C_ASSETS, _by_skill(skill_id))
            if p.get("filename")
        )
        return json.dumps(
            {
                **body,
                "tier3_manifest": {
                    "references": refs,
                    "scripts": scripts,
                    "assets": assets,
                },
            },
            indent=2,
        )

    async def _skills_get_options(skill_id: str) -> str:
        QU, QK = _creds()
        payloads = await _scroll(QU, QK, C_OPTS, _by_skill(skill_id), 1)
        if not payloads:
            return json.dumps(
                {"error": f"skill_id '{skill_id}' not found in options collection"}
            )
        return json.dumps(payloads[0], indent=2)

    async def _skills_get_reference(skill_id: str, filename: str = "list") -> str:
        QU, QK = _creds()
        if filename in ("list", "", "all"):
            payloads = await _scroll(QU, QK, C_REFS, _by_skill(skill_id))
            refs = sorted(
                [
                    {
                        "filename": p.get("filename", ""),
                        "description": p.get("description", ""),
                        "file_path": p.get("file_path", ""),
                    }
                    for p in payloads
                ],
                key=lambda r: r["filename"],
            )
            return json.dumps(
                {"skill_id": skill_id, "total": len(refs), "references": refs}, indent=2
            )

        payloads = await _scroll(QU, QK, C_REFS, _by_skill_file(skill_id, filename), 1)
        if not payloads:
            all_p = await _scroll(QU, QK, C_REFS, _by_skill(skill_id))
            match = next(
                (p for p in all_p if p.get("filename", "").lower() == filename.lower()),
                None,
            )
            if match:
                payloads = [match]

        if not payloads:
            all_p = await _scroll(QU, QK, C_REFS, _by_skill(skill_id))
            return json.dumps(
                {
                    "error": f"Reference '{filename}' not found for skill '{skill_id}'.",
                    "available": [p.get("filename") for p in all_p if p.get("filename")],
                }
            )

        p = payloads[0]
        return json.dumps(
            {
                "skill_id": p.get("skill_id", skill_id),
                "skill_name": p.get("skill_name", ""),
                "filename": p.get("filename", filename),
                "file_path": p.get("file_path", ""),
                "description": p.get("description", ""),
                "content": p.get("content", ""),
            },
            indent=2,
        )

    async def _skills_run_script(
        skill_id: str,
        filename: str = "list",
        input_data: dict | None = None,
        list_only: bool = False,
    ) -> str:
        QU, QK = _creds()
        payloads = await _scroll(QU, QK, C_SCRIPTS, _by_skill(skill_id))
        scripts = sorted(
            [
                {
                    "filename": p.get("filename", ""),
                    "language": p.get("language", "unknown"),
                    "description": p.get("description", ""),
                    "file_path": p.get("file_path", ""),
                    "dependencies": p.get("dependencies", []),
                }
                for p in payloads
            ],
            key=lambda s: s["filename"],
        )

        if list_only or filename in ("list", "", "all"):
            return json.dumps(
                {
                    "skill_id": skill_id,
                    "total": len(scripts),
                    "scripts": scripts,
                    "note": (
                        "Script execution is not available in Cloudflare Workers. "
                        "Run locally: MCP_TRANSPORT=streamable-http python -m skill_mcp.server"
                    ),
                },
                indent=2,
            )

        match = next(
            (
                s
                for s in scripts
                if s["filename"] == filename
                or s["filename"].lower() == filename.lower()
            ),
            None,
        )
        if not match:
            return json.dumps(
                {
                    "error": f"Script '{filename}' not found for skill '{skill_id}'.",
                    "available": [s["filename"] for s in scripts],
                }
            )

        return json.dumps(
            {
                "error": "Script execution is not supported in Cloudflare Workers.",
                "note": (
                    "Subprocess calls are unavailable in the Pyodide runtime. "
                    "Run locally: MCP_TRANSPORT=streamable-http python -m skill_mcp.server"
                ),
                "skill_id": skill_id,
                "filename": match["filename"],
                "language": match["language"],
            }
        )

    async def _skills_get_asset(skill_id: str, filename: str = "list") -> str:
        QU, QK = _creds()
        if filename in ("list", "", "all"):
            payloads = await _scroll(QU, QK, C_ASSETS, _by_skill(skill_id))
            assets = sorted(
                [
                    {
                        "filename": p.get("filename", ""),
                        "asset_type": p.get("asset_type", "other"),
                        "description": p.get("description", ""),
                        "file_path": p.get("file_path", ""),
                    }
                    for p in payloads
                ],
                key=lambda a: a["filename"],
            )
            return json.dumps(
                {"skill_id": skill_id, "total": len(assets), "assets": assets}, indent=2
            )

        payloads = await _scroll(QU, QK, C_ASSETS, _by_skill_file(skill_id, filename), 1)
        if not payloads:
            all_p = await _scroll(QU, QK, C_ASSETS, _by_skill(skill_id))
            match = next(
                (p for p in all_p if p.get("filename", "").lower() == filename.lower()),
                None,
            )
            if match:
                payloads = [match]

        if not payloads:
            all_p = await _scroll(QU, QK, C_ASSETS, _by_skill(skill_id))
            return json.dumps(
                {
                    "error": f"Asset '{filename}' not found for skill '{skill_id}'.",
                    "available": [p.get("filename") for p in all_p if p.get("filename")],
                }
            )

        p = payloads[0]
        return json.dumps(
            {
                "skill_id": p.get("skill_id", skill_id),
                "skill_name": p.get("skill_name", ""),
                "filename": p.get("filename", filename),
                "file_path": p.get("file_path", ""),
                "asset_type": p.get("asset_type", "other"),
                "description": p.get("description", ""),
                "content": p.get("content", ""),
            },
            indent=2,
        )

    # ── MCP JSON-RPC dispatcher ────────────────────────────────────────────────

    async def _call_tool(name: str, args: dict) -> str:
        if name == "skills_find_relevant":
            try:
                top_k = max(1, min(int(args.get("top_k", 5)), 20))
            except (TypeError, ValueError):
                top_k = 5
            return await _skills_find_relevant(
                query=str(args.get("query", "")),
                top_k=top_k,
            )
        elif name == "skills_get_body":
            return await _skills_get_body(
                skill_id=str(args.get("skill_id", "")),
                version=args.get("version") or None,
            )
        elif name == "skills_get_options":
            return await _skills_get_options(skill_id=str(args.get("skill_id", "")))
        elif name == "skills_get_reference":
            return await _skills_get_reference(
                skill_id=str(args.get("skill_id", "")),
                filename=str(args.get("filename", "list")),
            )
        elif name == "skills_run_script":
            return await _skills_run_script(
                skill_id=str(args.get("skill_id", "")),
                filename=str(args.get("filename", "list")),
                input_data=args.get("input_data"),
                list_only=bool(args.get("list_only", False)),
            )
        elif name == "skills_get_asset":
            return await _skills_get_asset(
                skill_id=str(args.get("skill_id", "")),
                filename=str(args.get("filename", "list")),
            )
        else:
            raise ValueError(f"Unknown tool: {name!r}")

    async def _handle_message(msg: dict) -> dict | None:
        """
        Process a JSON-RPC 2.0 message.
        Returns a response dict, or None for notifications (no response expected).
        """
        if not isinstance(msg, dict):
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
        method = str(msg.get("method", ""))
        msg_id = msg.get("id")  # absent on notifications
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        def ok(result: Any) -> dict:
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}

        def err(code: int, text: str) -> dict:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": text}}

        if method == "initialize":
            return ok(
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "skill-mcp-server", "version": "1.0.0"},
                }
            )

        elif method.startswith("notifications/"):
            return None  # Notifications require no response

        elif method == "ping":
            return ok({})

        elif method == "tools/list":
            return ok({"tools": _MCP_TOOLS})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                return err(-32602, "arguments must be an object")
            try:
                result_text = await _call_tool(tool_name, arguments)
                return ok(
                    {
                        "content": [{"type": "text", "text": result_text}],
                        "isError": False,
                    }
                )
            except ValueError as exc:
                # ValueError is raised for unknown tool names — safe to surface
                return ok(
                    {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    }
                )
            except Exception:
                # All other exceptions (upstream errors, network failures, etc.)
                # are intentionally suppressed to avoid leaking internal details
                # such as Qdrant cluster URLs, stack traces, or service config.
                return ok(
                    {
                        "content": [
                            {"type": "text", "text": "Tool execution failed. Check server logs."}
                        ],
                        "isError": True,
                    }
                )

        elif msg_id is not None:
            return err(-32601, f"Method not found: {method}")

        else:
            return None  # Unknown notification — ignore

    # ── Bare ASGI helpers ──────────────────────────────────────────────────────

    # Security headers added to every HTTP response
    _SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"cache-control", b"no-store"),
        (b"referrer-policy", b"no-referrer"),
    ]

    # CORS headers — required for browser-based MCP testers (Glama, etc.)
    _CORS_HEADERS: list[tuple[bytes, bytes]] = [
        (b"access-control-allow-origin", b"*"),
        (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
        (b"access-control-allow-headers", b"content-type, authorization, mcp-session-id, last-event-id"),
        (b"access-control-max-age", b"86400"),
    ]

    async def _send_response(
        send: Any,
        status: int,
        body: bytes,
        content_type: bytes = b"application/json",
        extra_headers: list | None = None,
    ) -> None:
        headers = [
            (b"content-type", content_type),
            *_SECURITY_HEADERS,
            *_CORS_HEADERS,
        ]
        if extra_headers:
            headers.extend(extra_headers)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body, "more_body": False})

    _MAX_REQUEST_BODY = 1_048_576  # 1 MB — reject oversized payloads before parsing

    async def _read_body(receive: Any) -> bytes:
        body = b""
        while True:
            event = await receive()
            body += event.get("body", b"")
            if len(body) > _MAX_REQUEST_BODY:
                raise RuntimeError("Request body exceeds 1 MB limit")
            if not event.get("more_body", False):
                return body

    def _parse_qs(query_string: str) -> dict[str, str]:
        params: dict[str, str] = {}
        # Limit overall query-string size and individual key/value lengths to
        # prevent oversized or injection-crafted session IDs from entering state.
        if len(query_string) > 2048:
            return params
        for part in query_string.split("&")[:16]:  # ignore >16 parameters
            if "=" in part:
                k, _, v = part.partition("=")
                k = urllib.parse.unquote_plus(k)[:128]
                v = urllib.parse.unquote_plus(v)[:256]
                params[k] = v
        return params

    # ── Route handlers ─────────────────────────────────────────────────────────

    async def _handle_sse(scope: dict, receive: Any, send: Any) -> None:
        """GET /sse — open SSE stream, send endpoint event, relay responses."""
        # Rate limit
        ip = _client_ip(scope)
        if not _check_rate_limit(ip):
            body = json.dumps({"error": "Too Many Requests"}).encode()
            await _send_response(send, 429, body)
            return

        session_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue()
        _sessions[session_id] = queue

        messages_url = f"/messages/?sessionId={session_id}"
        endpoint_event = f"event: endpoint\ndata: {messages_url}\n\n".encode()

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/event-stream; charset=utf-8"),
                    (b"cache-control", b"no-cache"),
                    (b"connection", b"keep-alive"),
                    (b"x-accel-buffering", b"no"),
                    # CORS — needed for browser clients
                    *_CORS_HEADERS,
                ],
            }
        )
        await send(
            {"type": "http.response.body", "body": endpoint_event, "more_body": True}
        )

        try:
            while True:
                item = await queue.get()
                if item is None:  # Sentinel: close the stream
                    break
                chunk = f"data: {json.dumps(item)}\n\n".encode()
                await send(
                    {"type": "http.response.body", "body": chunk, "more_body": True}
                )
        finally:
            _sessions.pop(session_id, None)

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _handle_mcp_post(scope: dict, receive: Any, send: Any) -> None:
        """POST /mcp — stateless Streamable HTTP transport (MCP spec 2025-03-26).

        Parses a JSON-RPC request, dispatches it synchronously, and returns
        the response as application/json. This is the mode used by Glama's
        inspector and any client built against the 2025-03-26 MCP spec.
        Sessions and server-push are not supported in stateless mode.
        """
        ip = _client_ip(scope)
        if not _check_rate_limit(ip):
            body = json.dumps({"error": "Too Many Requests"}).encode()
            await _send_response(send, 429, body)
            return

        try:
            raw = await _read_body(receive)
        except RuntimeError:
            body = json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Request body too large"}}).encode()
            await _send_response(send, 413, body)
            return
        try:
            message = json.loads(raw)
        except Exception:
            body = json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}).encode()
            await _send_response(send, 400, body)
            return

        response = await _handle_message(message)
        if response is None:
            # Notification — no body expected
            await _send_response(send, 204, b"", content_type=b"application/json")
            return

        await _send_response(send, 200, json.dumps(response).encode())

    async def _handle_messages(scope: dict, receive: Any, send: Any) -> None:
        """POST /messages/ — receive JSON-RPC, route response to SSE stream."""
        ip = _client_ip(scope)
        if not _check_rate_limit(ip):
            body = json.dumps({"error": "Too Many Requests"}).encode()
            await _send_response(send, 429, body)
            return

        qs = scope.get("query_string", b"").decode()
        params = _parse_qs(qs)
        session_id = params.get("sessionId", "")
        queue = _sessions.get(session_id)

        if queue is None:
            body = json.dumps({"error": "Session not found or expired"}).encode()
            await _send_response(send, 404, body)
            return

        try:
            raw = await _read_body(receive)
        except RuntimeError:
            err = json.dumps({"error": "Request body too large"}).encode()
            await _send_response(send, 413, err)
            return
        try:
            message = json.loads(raw)
        except Exception:
            body = json.dumps({"error": "Invalid JSON body"}).encode()
            await _send_response(send, 400, body)
            return

        response = await _handle_message(message)
        if response is not None:
            await queue.put(response)

        await _send_response(send, 202, b"", content_type=b"text/plain")

    # ── Bare ASGI callable ─────────────────────────────────────────────────────

    async def app(scope: dict, receive: Any, send: Any) -> None:
        scope_type = scope.get("type", "")

        if scope_type == "lifespan":
            # Acknowledge lifespan events without doing anything
            while True:
                event = await receive()
                if event["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif event["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        elif scope_type == "http":
            path = scope.get("path", "")
            method = scope.get("method", "").upper()

            # ── CORS preflight — must be first so browsers can reach any route ──
            if method == "OPTIONS":
                await _send_response(send, 204, b"", content_type=b"text/plain")
                return

            if path == "/sse" and method == "GET":
                await _handle_sse(scope, receive, send)
            elif path in ("/messages/", "/messages") and method == "POST":
                await _handle_messages(scope, receive, send)
            elif path == "/mcp" and method == "POST":
                # Streamable HTTP transport (MCP spec 2025-03-26)
                await _handle_mcp_post(scope, receive, send)
            else:
                body = json.dumps({"error": "Not found"}).encode()
                await _send_response(send, 404, body)

        else:
            # Unrecognised ASGI scope type — ignore
            pass

    return app


# ── Durable Object ────────────────────────────────────────────────────────────


class SkillMCPServer(DurableObject):
    """Holds the ASGI app and SSE session state for skill-mcp."""

    def __init__(self, ctx: Any, env: Any) -> None:
        self.ctx = ctx
        self.env = env
        self._app = _build_server(env)

    async def on_fetch(self, request: Any, env: Any, ctx: Any) -> Any:
        import asgi

        return await asgi.fetch(self._app, request, self.env, self.ctx)


# ── Worker entry point ────────────────────────────────────────────────────────


async def on_fetch(request: Any, env: Any) -> Any:
    """Route all requests to the singleton Durable Object."""
    obj_id = env.MCP_OBJECT.idFromName("skill-mcp")
    obj = env.MCP_OBJECT.get(obj_id)
    return await obj.fetch(request)
