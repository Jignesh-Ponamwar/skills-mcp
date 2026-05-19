"""
skill-mcp local server - Python FastMCP entry point.

This is the **local development** server. The production server is the
Cloudflare Worker in src/worker.py - deploy it with `wrangler deploy`.

Use this local server when you need script execution support: the Worker
runs on Cloudflare's Python (Pyodide) runtime which cannot spawn subprocesses,
so `skills_run_script` execution mode requires running locally.

Seven MCP tools:
  skills_find_relevant  - semantic search (via Cloudflare Workers AI REST API)
  skills_list_all       - browse full catalogue without search
  skills_get_body       - full instructions + tier3_manifest
  skills_get_options    - config variants, dependencies, limitations
  skills_get_reference  - fetch a reference markdown file
  skills_run_script     - execute a bundled script (sandboxed subprocess)
  skills_get_asset      - fetch a template or static resource

Transport (set MCP_TRANSPORT env var):
  stdio            (default) - Claude Code, Cursor, any local MCP client
  streamable-http            - networked / remote use

Required env vars (.env):
  QDRANT_URL, QDRANT_API_KEY  - Qdrant Cloud credentials
  WORKERS_AI_ACCOUNT_ID, WORKERS_AI_API_TOKEN - Cloudflare credentials (for embedding)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator, Optional

from pydantic import Field

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
from .tools.list_all_skills import list_all_skills
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
            "Server will start anyway - tool calls will fail if Qdrant is unreachable.",
            file=sys.stderr,
        )
    yield
    # No teardown needed - Qdrant connections are stateless HTTP


# ── FastMCP app ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="skill-mcp-server",
    instructions=(
        "SKILLS REGISTRY — Expert procedures for engineering tasks.\n\n"
        "TOOL CALL ORDER IS MANDATORY. Skipping steps causes irrelevant skills to load,\n"
        "wasting tokens and degrading task quality. Follow the workflow exactly.\n\n"
        "═══ STEP 1 — ALWAYS FIRST: skills_find_relevant ═════════════════════════\n"
        "  Call before ANY other skills_ tool — no exceptions.\n"
        "  This is the ONLY valid source of skill_ids. Skill_ids from skills_list_all\n"
        "  are NOT verified for relevance and MUST NOT be passed to skills_get_body.\n"
        "  After getting results, check the score:\n"
        "    score > 0.6  → strong match → proceed to Step 2\n"
        "    score 0.4–0.6 → read description, then decide\n"
        "    score < 0.4  → no match → proceed without a skill\n\n"
        "═══ STEP 2 — only after Step 1 score > 0.6: skills_get_body ═════════════\n"
        "  Load full instructions using ONLY a skill_id returned by Step 1.\n"
        "  Read the entire instructions field and follow it precisely.\n\n"
        "═══ STEP 3 — only if body names a file: Tier-3 tools ════════════════════\n"
        "  skills_get_reference / skills_run_script / skills_get_asset\n"
        "  Call ONLY when Step 2 instructions explicitly say 'see FILE.md' or\n"
        "  'run FILE.py'. Do NOT load Tier-3 files speculatively.\n\n"
        "BROWSING (optional): skills_list_all() shows the full catalogue.\n"
        "  After browsing, you MUST still call skills_find_relevant to get a\n"
        "  relevance score before loading anything with skills_get_body.\n\n"
        "FORBIDDEN ACTIONS:\n"
        "  ✗ Calling skills_get_body without a prior skills_find_relevant score > 0.6\n"
        "  ✗ Passing skill_ids from skills_list_all directly to skills_get_body\n"
        "  ✗ Guessing or inventing skill_ids\n"
        "  ✗ Loading Tier-3 files unless body instructions explicitly name them\n"
        "  ✗ Skipping skills_find_relevant even if you think you know the skill_id\n\n"
        "QUERY TIPS: Be specific. 'pytest tests for FastAPI with JWT auth' works.\n"
        "  'testing' does not. Describe the task, not the category."
    ),
    lifespan=lifespan,
)


# ── Tool registrations ────────────────────────────────────────────────────────

@mcp.tool(
    name="skills_find_relevant",
    description=(
        "ALWAYS CALL THIS FIRST — before any other skills_ tool, no exceptions.\n\n"
        "This is the ONLY valid source of skill_ids. Do NOT use skill_ids from\n"
        "skills_list_all without first running this search to verify relevance.\n\n"
        "Returns ranked results with similarity scores. Required next actions:\n"
        "  score > 0.6  → call skills_get_body with that skill_id\n"
        "  score 0.4–0.6 → read the description, then decide whether to load\n"
        "  score < 0.4  → no match, proceed without a skill\n\n"
        "Query tips: be specific about the task.\n"
        "  GOOD: 'implement Stripe webhook signature verification in Python'\n"
        "  BAD:  'stripe' — too vague, produces poor matches."
    ),
)
def _skills_find_relevant(
    query: Annotated[str, Field(description=(
        "Natural language description of the task you need help with. "
        "Be specific: 'write pytest integration tests for a FastAPI async endpoint' "
        "not just 'testing'. Describe what you need to accomplish, not the category."
    ))],
    top_k: Annotated[int, Field(default=5, ge=1, le=20, description=(
        "Number of results to return (1-20). Default 5 is usually sufficient."
    ))] = 5,
) -> str:
    return find_relevant_skills(query=query, top_k=top_k)


@mcp.tool(
    name="skills_get_body",
    description=(
        "Load full skill instructions. Call ONLY after skills_find_relevant returns\n"
        "this skill_id with score > 0.6.\n\n"
        "REQUIRED PREREQUISITES — both must be true before calling this tool:\n"
        "  1. You called skills_find_relevant with a specific query\n"
        "  2. This skill_id appeared in those results with score > 0.6\n\n"
        "If either prerequisite is missing, STOP and call skills_find_relevant first.\n"
        "Calling this tool with an unverified skill_id (e.g. one from skills_list_all\n"
        "or a guessed ID) will load a skill that may be completely irrelevant to your\n"
        "task, wasting tokens and producing wrong output.\n\n"
        "Returns:\n"
        "  - instructions: step-by-step expert guidance — read and follow entirely\n"
        "  - tier3_manifest: available reference files, scripts, assets\n\n"
        "After loading: follow the instructions precisely. Call Tier-3 tools ONLY\n"
        "when the instructions explicitly name a specific file."
    ),
)
def _skills_get_body(
    skill_id: Annotated[str, Field(description=(
        "The exact skill_id string returned by skills_find_relevant. "
        "Must come from search results with score > 0.6. "
        "Format: lowercase-kebab-case (e.g. 'api-integration', 'test-writer'). "
        "Do NOT guess or use IDs from skills_list_all without prior search."
    ))],
    version: Annotated[Optional[str], Field(default=None, description=(
        "Optional version pin (e.g. '1.2'). If omitted, returns latest. "
        "Can also be specified inline: 'skill-id@1.2'."
    ))] = None,
) -> str:
    return get_skill_body(skill_id=skill_id, version=version)


@mcp.tool(
    name="skills_get_options",
    description=(
        "OPTIONAL — Load config variants and constraints for a skill.\n\n"
        "REQUIRED PREREQUISITES — all must be true before calling this tool:\n"
        "  1. You called skills_find_relevant and got a score > 0.6\n"
        "  2. The skill_id came from those search results\n"
        "  3. The user asked about configuration, or skills_get_body mentioned options\n\n"
        "Do NOT call by default. Most tasks complete with skills_get_body alone."
    ),
)
def _skills_get_options(
    skill_id: Annotated[str, Field(description=(
        "The skill_id from skills_find_relevant results. "
        "Format: lowercase-kebab-case (e.g. 'api-integration')."
    ))],
) -> str:
    return get_skill_options(skill_id=skill_id)


@mcp.tool(
    name="skills_get_reference",
    description=(
        "Fetch a reference document bundled with a skill.\n\n"
        "STRICT PREREQUISITES — ALL THREE must be true before calling this tool:\n"
        "  1. You called skills_find_relevant and received a score > 0.6\n"
        "  2. You called skills_get_body and read the full instructions\n"
        "  3. Those instructions explicitly say 'see FILENAME.md' or 'refer to FILENAME'\n\n"
        "If any prerequisite is missing, do NOT call this tool.\n"
        "Speculative loading wastes tokens and does not improve task quality.\n\n"
        "Pass filename='list' to see available reference files for a skill."
    ),
)
def _skills_get_reference(
    skill_id: Annotated[str, Field(description=(
        "The skill_id from skills_find_relevant results."
    ))],
    filename: Annotated[str, Field(default="list", description=(
        "The reference filename to fetch (e.g. 'PAGINATION.md'). "
        "Pass 'list' to see all available reference files for this skill."
    ))] = "list",
) -> str:
    return get_skill_reference(skill_id=skill_id, filename=filename)


@mcp.tool(
    name="skills_run_script",
    description=(
        "Execute a helper script bundled with a skill.\n\n"
        "STRICT PREREQUISITES — ALL THREE must be true before calling this tool:\n"
        "  1. You called skills_find_relevant and received a score > 0.6\n"
        "  2. You called skills_get_body and read the full instructions\n"
        "  3. Those instructions explicitly direct you to run a specific script file\n\n"
        "If any prerequisite is missing, do NOT call this tool.\n\n"
        "Script source is NEVER returned — only stdout, stderr, and exit_code.\n"
        "Scripts run sandboxed in an isolated temp directory with a 30-second timeout.\n\n"
        "Two-phase use:\n"
        "  1. filename='list' → see available scripts and descriptions\n"
        "  2. filename='<script.py>' + optional input_data → execute\n\n"
        "input_data: key-value pairs passed to the script as environment variables."
    ),
)
def _skills_run_script(
    skill_id: Annotated[str, Field(description=(
        "The skill_id from skills_find_relevant results."
    ))],
    filename: Annotated[str, Field(default="list", description=(
        "The script filename to execute (e.g. 'extract.py', 'validate.js'). "
        "Pass 'list' to see available scripts and their descriptions."
    ))] = "list",
    input_data: Annotated[Optional[dict], Field(default=None, description=(
        "Key-value pairs passed to the script as environment variables. "
        "Example: {'PDF_PATH': '/tmp/report.pdf', 'OUTPUT_FORMAT': 'csv'}. "
        "Values are stringified before passing."
    ))] = None,
    list_only: Annotated[bool, Field(default=False, description=(
        "If true, return the script manifest without executing. "
        "Same as passing filename='list'."
    ))] = False,
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
        "Fetch a template or static resource bundled with a skill\n"
        "(markdown templates, config starters, example data files).\n\n"
        "STRICT PREREQUISITES — ALL THREE must be true before calling this tool:\n"
        "  1. You called skills_find_relevant and received a score > 0.6\n"
        "  2. You called skills_get_body and read the full instructions\n"
        "  3. Those instructions explicitly reference a specific asset file\n\n"
        "If any prerequisite is missing, do NOT call this tool.\n\n"
        "Two-phase use:\n"
        "  1. filename='list' → see the full asset manifest\n"
        "  2. filename='<file>' → fetch content (use as a starting template, adapt to task)"
    ),
)
def _skills_get_asset(
    skill_id: Annotated[str, Field(description=(
        "The skill_id from skills_find_relevant results."
    ))],
    filename: Annotated[str, Field(default="list", description=(
        "The asset filename to fetch (e.g. 'report-template.md'). "
        "Pass 'list' to see all available assets for this skill."
    ))] = "list",
) -> str:
    return get_skill_asset(skill_id=skill_id, filename=filename)


@mcp.tool(
    name="skills_list_all",
    description=(
        "BROWSING — See all available skills without semantic search.\n\n"
        "Use when you want to explore the full registry by category or tag.\n\n"
        "WARNING: skill_ids returned here have NOT been scored for relevance to your\n"
        "current task. After browsing, you MUST still call skills_find_relevant to\n"
        "verify relevance before loading any skill with skills_get_body.\n"
        "Do NOT pass skill_ids from this listing directly to skills_get_body.\n\n"
        "Returns lightweight frontmatter (skill_id, name, tags, complexity_level,\n"
        "has_tier3) to keep token usage reasonable.\n\n"
        "Supports pagination: use offset to skip results, limit to control batch size."
    ),
)
def _skills_list_all(
    limit: Annotated[int, Field(default=100, ge=1, le=100, description=(
        "Number of skills to return per page (1-100). Default 100."
    ))] = 100,
    offset: Annotated[int, Field(default=0, ge=0, description=(
        "Number of skills to skip (for pagination). Default 0."
    ))] = 0,
) -> str:
    return list_all_skills(limit=limit, offset=offset)


# ── Prompts ───────────────────────────────────────────────────────────────────

@mcp.prompt(
    name="skill_workflow",
    description=(
        "How to use the Skills MCP server. Call this prompt when you need to "
        "understand the correct tool-calling workflow for finding and loading skills."
    ),
)
def _skill_workflow_prompt() -> str:
    return (
        "You are about to use the Skills MCP server. Follow this EXACT sequence:\n\n"
        "STEP 1 — DISCOVER (mandatory, always first):\n"
        "  Call: skills_find_relevant(query='<specific task description>')\n"
        "  Example: skills_find_relevant(query='write pytest integration tests for FastAPI')\n"
        "  Check the score of the top result:\n"
        "    - score > 0.6  → proceed to Step 2 with that skill_id\n"
        "    - score 0.4–0.6 → read the description, decide if relevant\n"
        "    - score < 0.4  → no matching skill exists, proceed without one\n\n"
        "STEP 2 — LOAD (only if Step 1 returned score > 0.6):\n"
        "  Call: skills_get_body(skill_id='<skill_id from Step 1>')\n"
        "  Read the 'instructions' field entirely and follow it precisely.\n"
        "  Note the 'tier3_manifest' field — it lists supplementary files.\n\n"
        "STEP 3 — SUPPLEMENT (only if Step 2 instructions name a specific file):\n"
        "  - Reference docs: skills_get_reference(skill_id, filename='<file.md>')\n"
        "  - Run scripts: skills_run_script(skill_id, filename='<script.py>', input_data={})\n"
        "  - Templates: skills_get_asset(skill_id, filename='<template.md>')\n"
        "  Only call these if the body instructions explicitly say 'see FILE' or 'run FILE'.\n\n"
        "CRITICAL RULES:\n"
        "  - NEVER skip Step 1 — even if you think you know the skill_id\n"
        "  - NEVER use skill_ids from skills_list_all without running Step 1 first\n"
        "  - NEVER call Tier-3 tools without completing Steps 1 and 2\n"
        "  - NEVER guess or invent skill_ids\n"
    )


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
