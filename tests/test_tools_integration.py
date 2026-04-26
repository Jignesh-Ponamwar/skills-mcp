"""
Integration tests for the six MCP tool functions.

These tests require a live Qdrant instance. They are skipped automatically
when QDRANT_URL is not set or CI_SKIP_INTEGRATION=1 is set.

The embedder is mocked with a fixed vector so that Cloudflare credentials
are not required to run these tests.

Run locally:
    QDRANT_URL=http://localhost:6333 pytest tests/test_tools_integration.py -v

Or against Qdrant Cloud (requires credentials in .env):
    pytest tests/test_tools_integration.py -v
"""

from __future__ import annotations

import json
import os

import pytest

# Skip if Qdrant is explicitly disabled or URL not configured
_skip = pytest.mark.skipif(
    os.getenv("CI_SKIP_INTEGRATION") == "1"
    or not os.getenv("QDRANT_URL"),
    reason="Integration tests require QDRANT_URL to be set (CI_SKIP_INTEGRATION=1 skips)",
)

pytestmark = _skip

# Fixed 384-dim vector for deterministic tests — avoids calling Cloudflare Workers AI
_FIXED_VECTOR: list[float] = [0.01] * 384


@pytest.fixture(scope="module", autouse=True)
def setup_test_collections(monkeypatch_module):
    """Seed a minimal skill into test-prefixed collections, then tear down."""
    os.environ["FRONTMATTER_COLLECTION"] = "test_skill_frontmatter"
    os.environ["BODY_COLLECTION"] = "test_skill_body"
    os.environ["OPTIONS_COLLECTION"] = "test_skill_options"
    os.environ["REFERENCES_COLLECTION"] = "test_skill_references"
    os.environ["SCRIPTS_COLLECTION"] = "test_skill_scripts"
    os.environ["ASSETS_COLLECTION"] = "test_skill_assets"

    # Patch embedder so no Cloudflare API calls are made during tests.
    # embed() and embed_batch() both delegate to _call_api_batch internally.
    from skill_mcp.db import embedder as embedder_module
    monkeypatch_module.setattr(
        embedder_module.embedder,
        "_call_api_batch",
        lambda texts: [_FIXED_VECTOR] * len(texts),
    )

    from skill_mcp.db.embedder import embedder
    from skill_mcp.db.qdrant_manager import qdrant_manager
    from skill_mcp.models.skill import (
        SkillFrontMatter,
        SkillBody,
        SkillOptions,
    )

    qdrant_manager.connect()
    qdrant_manager.ensure_collections()

    # Seed one test skill using the correct separate models
    fm = SkillFrontMatter(
        skill_id="pytest-skill",
        name="Pytest Skill",
        description="Generates pytest test cases for Python functions",
        trigger_phrases=["write pytest tests", "unit tests for python"],
        tags=["testing", "pytest"],
        platforms=["cli"],
    )
    body = SkillBody(
        skill_id="pytest-skill",
        instructions="Generate comprehensive pytest suites for the given code.",
        system_prompt_addition="You are a test engineer specialising in pytest.",
    )
    options = SkillOptions(
        skill_id="pytest-skill",
        config_schema={"framework": {"type": "string", "default": "pytest"}},
        variants=[{"name": "tdd", "description": "TDD mode"}],
        dependencies=["pytest"],
        limitations=["Static analysis only — no runtime execution"],
    )

    vector = embedder.embed(fm.description + " " + " ".join(fm.trigger_phrases))
    qdrant_manager.upsert_many_frontmatter([(fm, vector)])
    qdrant_manager.upsert_many_body([body])
    qdrant_manager.upsert_many_options([options])

    yield

    # Teardown: remove test collections
    client = qdrant_manager.client
    for col in (
        "test_skill_frontmatter",
        "test_skill_body",
        "test_skill_options",
        "test_skill_references",
        "test_skill_scripts",
        "test_skill_assets",
    ):
        try:
            client.delete_collection(col)
        except Exception:
            pass


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest only provides function-scoped by default)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


# ── skills_find_relevant ──────────────────────────────────────────────────────

def test_find_relevant_returns_results():
    from skill_mcp.tools.find_skills import find_relevant_skills

    result = json.loads(find_relevant_skills("write unit tests for my python code"))
    assert result["total_found"] >= 1
    assert result["results"][0]["skill_id"] == "pytest-skill"


def test_find_relevant_includes_score():
    from skill_mcp.tools.find_skills import find_relevant_skills

    result = json.loads(find_relevant_skills("unit test generation"))
    assert result["results"][0]["score"] is not None
    assert 0.0 <= result["results"][0]["score"] <= 1.0


def test_find_relevant_respects_top_k():
    from skill_mcp.tools.find_skills import find_relevant_skills

    result = json.loads(find_relevant_skills("testing", top_k=1))
    assert len(result["results"]) <= 1


def test_find_relevant_cache_hit(monkeypatch):
    from skill_mcp.tools import find_skills as module

    search_calls = []
    original = module.qdrant_manager.search_frontmatter

    def counting_search(*args, **kwargs):
        search_calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(module.qdrant_manager, "search_frontmatter", counting_search)
    module._search_cache.clear()

    module.find_relevant_skills("unique cache test query xyz123")
    module.find_relevant_skills("unique cache test query xyz123")

    assert len(search_calls) == 1  # second call served from cache


# ── skills_get_body ───────────────────────────────────────────────────────────

def test_get_body_returns_instructions():
    from skill_mcp.tools.get_skill_body import get_skill_body

    result = json.loads(get_skill_body("pytest-skill"))
    assert result["skill_id"] == "pytest-skill"
    assert "pytest" in result["instructions"].lower()
    assert "tier3_manifest" in result


def test_get_body_not_found():
    from skill_mcp.tools.get_skill_body import get_skill_body

    result = json.loads(get_skill_body("does-not-exist-skill"))
    assert "error" in result


def test_get_body_cache_hit(monkeypatch):
    from skill_mcp.tools import get_skill_body as module

    lookup_calls = []
    original = module.qdrant_manager.get_body

    def counting_lookup(*args, **kwargs):
        lookup_calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(module.qdrant_manager, "get_body", counting_lookup)
    module._body_cache.clear()

    module.get_skill_body("pytest-skill")
    module.get_skill_body("pytest-skill")

    assert len(lookup_calls) == 1


# ── skills_get_options ────────────────────────────────────────────────────────

def test_get_options_returns_schema():
    from skill_mcp.tools.get_skill_options import get_skill_options

    result = json.loads(get_skill_options("pytest-skill"))
    assert result["skill_id"] == "pytest-skill"
    assert "framework" in result["config_schema"]
    assert len(result["variants"]) >= 1
    assert "pytest" in result["dependencies"]


def test_get_options_not_found():
    from skill_mcp.tools.get_skill_options import get_skill_options

    result = json.loads(get_skill_options("ghost-skill"))
    assert "error" in result


def test_get_options_cache_hit(monkeypatch):
    from skill_mcp.tools import get_skill_options as module

    lookup_calls = []
    original = module.qdrant_manager.get_options

    def counting_lookup(*args, **kwargs):
        lookup_calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(module.qdrant_manager, "get_options", counting_lookup)
    module._options_cache.clear()

    module.get_skill_options("pytest-skill")
    module.get_skill_options("pytest-skill")

    assert len(lookup_calls) == 1
