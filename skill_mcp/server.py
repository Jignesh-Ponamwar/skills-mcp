"""
skill-mcp local server — Python FastMCP entry point.

This is the **local development** server. The production server is the
Cloudflare Worker in src/worker.py — deploy it with `wrangler deploy`.

Use this local server when you need script execution support: the Worker
runs on Cloudflare's Python (Pyodide) runtime which cannot spawn subprocesses,
so `skills_run_script` execution mode requires running locally.

Six MCP tools:
  skills_find_relevant  — semantic search (via Cloudflare Workers AI REST API)
  skills_get_body       — full instructions + tier3_manifest
  skills_get_options    — config variants, dependencies, limitations
  skills_get_reference  — fetch a reference markdown file
  skills_run_script     — execute a bundled script (sandboxed subprocess)
  skills_get_asset      — fetch a template or static resource

Transport (set MCP_TRANSPORT env var):
  stdio            (default) — Claude Code, Cursor, any local MCP client
  streamable-http            — networked / remote use

Required env vars (.env):
  QDRANT_URL, QDRANT_API_KEY  — Qdrant Cloud credentials
  WORKERS_AI_ACCOUNT_ID, WORKERS_AI_API_TOKEN — Cloudflare credentials (for embedding)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastmcp import FastMCP

# load_dotenv() MUST run before the relative imports below.
# Those modules read os.getenv() at import time (module-level TTLCache, timeouts, etc.).
# Conditional import: python-dotenv may be absent in Docker / production environments
# where env vars are injected directly, and on Python 3.14 preview builds where
# python-dotenv 1.2.2 has a namespace resolution issue.  Missing dotenv is harmless
# when env vars are already set; the server will still start correctly.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# pylint: disable=wrong-import-position
from .db.qdrant_manager import qdrant_manager
from .tools.find_skills import find_relevant_skills
from .tools.get_skill_body import get_skill_body
from .tools.get_skill_options import get_skill_options
from .tools.get_skill_reference import get_skill_reference
from .tools.get_skill_asset import get_skill_asset
from .tools.run_skill_script import run_skill_script
# pylint: enable=wrong-import-position


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Connect to Qdrant Cloud on startup. Embeddings use Workers AI REST API.

    Startup errors (bad credentials, unreachable cluster) are logged but do NOT
    crash the server.  This lets Glama's build-test complete the MCP handshake
    and introspect tools with dummy credentials.  Real tool calls that reach
    Qdrant will return a graceful error if the connection is unavailable.
    """
    try:
        qdrant_manager.connect()
        qdrant_manager.ensure_collections()
    except Exception as exc:  # noqa: BLE001
        import sys
        print(
            f"[skill-mcp] WARNING: Qdrant startup check failed ({type(exc).__name__}: {exc}). "
            "Server will start anyway — tool calls will fail if Qdrant is unreachable.",
            file=sys.stderr,
        )
    yield
    # No teardown needed — Qdrant connections are stateless HTTP


# ── FastMCP app ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="skill-mcp-server",
    instructions=(
        "Skills registry with progressive disclosure.\n\n"
        "1. Call skills_find_relevant to discover skills relevant to your task.\n"
        "2. Call skills_get_body to load full instructions for a chosen skill. "
        "   The response includes tier3_manifest listing available references, "
        "   scripts, and assets.\n"
        "3. Call skills_get_reference, skills_run_script, or skills_get_asset "
        "   for supplementary material referenced in the body instructions.\n"
        "4. Optionally call skills_get_options for config schema and variants."
    ),
    lifespan=lifespan,
)


# ── Tool registrations ────────────────────────────────────────────────────────

@mcp.tool(
    name="skills_find_relevant",
    description=(
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
)
def _skills_find_relevant(query: str, top_k: int = 5) -> str:
    return find_relevant_skills(query=query, top_k=top_k)


@mcp.tool(
    name="skills_get_body",
    description=(
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
)
def _skills_get_body(skill_id: str, version: Optional[str] = None) -> str:
    return get_skill_body(skill_id=skill_id, version=version)


@mcp.tool(
    name="skills_get_options",
    description=(
        "OPTIONAL STEP 2b — Load config schema, variants, and constraints for a skill. "
        "Call only when: (a) the user asks to customise skill behaviour, or "
        "(b) skills_get_body instructions mention configurable options.\n\n"
        "Returns: config_schema (JSON Schema for parameters), "
        "variants (alternative skill modes), "
        "dependencies (required tools/packages), "
        "limitations (known constraints).\n\n"
        "Do NOT call this by default — most tasks complete with skills_get_body alone."
    ),
)
def _skills_get_options(skill_id: str) -> str:
    return get_skill_options(skill_id=skill_id)


@mcp.tool(
    name="skills_get_reference",
    description=(
        "STEP 3a — Fetch a reference document bundled with a skill "
        "(markdown files: checklists, policies, API specs, examples).\n\n"
        "Two-phase use:\n"
        "  1. Call with filename='list' (default) to see the full reference manifest\n"
        "  2. Call again with the specific filename to fetch its content\n\n"
        "Only call when: tier3_manifest from skills_get_body lists reference files "
        "AND the skill instructions explicitly name one. "
        "Do not load references speculatively."
    ),
)
def _skills_get_reference(skill_id: str, filename: str = "list") -> str:
    return get_skill_reference(skill_id=skill_id, filename=filename)


@mcp.tool(
    name="skills_run_script",
    description=(
        "STEP 3b — Execute a helper script bundled with a skill. "
        "Script source is NEVER returned — only stdout, stderr, and exit_code.\n\n"
        "Two-phase use:\n"
        "  1. Call with filename='list' to see available scripts and their descriptions\n"
        "  2. Call with the specific filename (and optional input_data) to execute\n\n"
        "input_data: key-value pairs passed to the script as environment variables. "
        "Scripts run sandboxed in an isolated temp directory with a 30-second hard timeout.\n\n"
        "Only call when skill instructions direct you to run a specific script."
    ),
)
def _skills_run_script(
    skill_id: str,
    filename: str = "list",
    input_data: dict | None = None,
    list_only: bool = False,
) -> str:
    return run_skill_script(
        skill_id=skill_id,
        filename=filename,
        input_data=input_data,
        list_only=list_only,
    )


@mcp.tool(
    name="skills_get_asset",
    description=(
        "STEP 3c — Fetch a template or static resource bundled with a skill "
        "(markdown templates, config starters, example data files).\n\n"
        "Two-phase use:\n"
        "  1. Call with filename='list' (default) to see the full asset manifest\n"
        "  2. Call again with the specific filename to fetch its content\n\n"
        "Use the returned content as a starting template — adapt it to the specific task. "
        "Only call when skill instructions reference a specific asset file."
    ),
)
def _skills_get_asset(skill_id: str, filename: str = "list") -> str:
    return get_skill_asset(skill_id=skill_id, filename=filename)


# ── Transport ─────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the FastMCP server using the transport configured in MCP_TRANSPORT."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
