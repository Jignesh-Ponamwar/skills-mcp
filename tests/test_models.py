"""Unit tests for Pydantic models — no external deps required."""

import pytest

from skill_mcp.models.skill import (
    SearchResponse,
    SkillBody,
    SkillFrontMatter,
    SkillOptions,
    SkillRecord,
)


def _sample_record() -> SkillRecord:
    return SkillRecord(
        skill_id="test-skill",
        name="Test Skill",
        description="A test skill for unit testing",
        trigger_phrases=["test trigger"],
        tags=["test"],
        platforms=["cli"],
        instructions="Do the thing.",
        system_prompt_addition="You are a tester.",
        example_usage="Test everything.",
        config_schema={"mode": {"type": "string", "default": "fast"}},
        variants=[{"name": "v1", "description": "variant one"}],
        dependencies=["dep-a"],
        limitations=["limited to tests"],
    )


def test_skill_record_to_frontmatter():
    rec = _sample_record()
    fm = rec.to_frontmatter()
    assert fm.skill_id == "test-skill"
    assert fm.name == "Test Skill"
    assert fm.trigger_phrases == ["test trigger"]
    assert fm.score is None  # not set until search


def test_skill_record_to_body():
    rec = _sample_record()
    body = rec.to_body()
    assert body.skill_id == "test-skill"
    assert body.instructions == "Do the thing."
    assert body.system_prompt_addition == "You are a tester."


def test_skill_record_to_options():
    rec = _sample_record()
    opts = rec.to_options()
    assert opts.skill_id == "test-skill"
    assert "mode" in opts.config_schema
    assert len(opts.variants) == 1
    assert opts.dependencies == ["dep-a"]
    assert opts.limitations == ["limited to tests"]


def test_frontmatter_json_excludes_none_score():
    fm = SkillFrontMatter(
        skill_id="x", name="X", description="desc"
    )
    data = fm.model_dump()
    assert "score" in data
    assert data["score"] is None


def test_frontmatter_with_score():
    fm = SkillFrontMatter(
        skill_id="x", name="X", description="desc", score=0.92
    )
    assert fm.score == pytest.approx(0.92)


def test_search_response_serialization():
    fm = SkillFrontMatter(skill_id="a", name="A", description="desc", score=0.8)
    resp = SearchResponse(query="test", results=[fm], total_found=1)
    d = resp.model_dump()
    assert d["total_found"] == 1
    assert d["results"][0]["skill_id"] == "a"


def test_skill_body_defaults():
    body = SkillBody(skill_id="b", instructions="step 1")
    assert body.system_prompt_addition == ""
    assert body.example_usage == ""


def test_skill_options_defaults():
    opts = SkillOptions(skill_id="c")
    assert opts.config_schema == {}
    assert opts.variants == []
    assert opts.dependencies == []
    assert opts.limitations == []
