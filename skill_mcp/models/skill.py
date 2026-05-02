from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Tier-1: Discovery ─────────────────────────────────────────────────────────

class SkillFrontMatter(BaseModel):
    """Lightweight descriptor stored with a vector for semantic search.

    Returned by skills_find_relevant. Never contains the full instruction body
    — agents must call skills_get_body(skill_id) for that.
    """

    skill_id: str
    name: str
    description: str
    trigger_phrases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    version: str = "1.0"
    author: str = ""
    license: str = "Apache-2.0"
    # skill:// URI for MCP SkillsProvider compatibility
    skill_uri: str = ""
    score: Optional[float] = None  # populated after vector search
    # Deprecation — set in SKILL.md frontmatter when a skill is superseded
    deprecated: bool = False
    replaced_by: str = ""  # skill_id of the replacement, or "" if none


# ── Tier-2: Body + Options ────────────────────────────────────────────────────

class SkillBody(BaseModel):
    """Full instructions — fetched on demand by skill_id, no vector needed."""

    skill_id: str
    instructions: str
    system_prompt_addition: str = ""
    example_usage: str = ""


class SkillOptions(BaseModel):
    """Config variants, deps, limitations — optional deep-dive per skill."""

    skill_id: str
    config_schema: dict[str, Any] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# ── Tier-3: References, Scripts, Assets ──────────────────────────────────────

class SkillReference(BaseModel):
    """A reference markdown file bundled inside a skill folder (references/*.md).

    Stored in the skill_references collection. Content is returned in full when
    skills_get_reference is called with a specific filename.
    """

    skill_id: str
    skill_name: str = ""
    filename: str                   # e.g. "FORMS.md", "POLICY.md"
    content: str                    # full markdown content
    description: str = ""           # parsed from first heading or paragraph
    file_path: str = ""             # relative path e.g. "references/FORMS.md"


class SkillScript(BaseModel):
    """An executable script bundled inside a skill folder (scripts/*.py etc.).

    IMPORTANT: The source field is stored here but must NEVER be returned to
    the agent by skills_run_script — only execution output is returned.
    """

    skill_id: str
    skill_name: str = ""
    filename: str                           # e.g. "extract.py"
    language: str                           # python | javascript | bash | unknown
    source: str                             # full script source — internal only
    description: str = ""                   # parsed from first docstring/comment
    file_path: str = ""                     # e.g. "scripts/extract.py"
    dependencies: list[str] = Field(default_factory=list)  # best-effort parsed imports


class SkillAsset(BaseModel):
    """A template or static resource bundled inside a skill folder (assets/*).

    Returned in full when skills_get_asset is called with a specific filename.
    """

    skill_id: str
    skill_name: str = ""
    filename: str                   # e.g. "report-template.md"
    content: str                    # full file content
    asset_type: str = "other"       # template | config | data | other
    description: str = ""           # parsed from first line or heading
    file_path: str = ""             # e.g. "assets/report-template.md"


# ── Aggregates ────────────────────────────────────────────────────────────────

class SkillRecord(BaseModel):
    """Convenience aggregate combining all three tier layers into one model.

    SKILL.md seeding constructs SkillFrontMatter, SkillBody, and SkillOptions
    directly. This class is useful for testing and for programmatic skill
    creation where all fields are known upfront; use to_frontmatter(),
    to_body(), and to_options() to split it into the three storage models.
    """

    skill_id: str
    name: str
    description: str
    trigger_phrases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    version: str = "1.0"
    author: str = ""
    license: str = "Apache-2.0"
    instructions: str
    system_prompt_addition: str = ""
    example_usage: str = ""
    config_schema: dict[str, Any] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    deprecated: bool = False
    replaced_by: str = ""

    def to_frontmatter(self) -> SkillFrontMatter:
        return SkillFrontMatter(
            skill_id=self.skill_id,
            name=self.name,
            description=self.description,
            trigger_phrases=self.trigger_phrases,
            tags=self.tags,
            platforms=self.platforms,
            version=self.version,
            author=self.author,
            license=self.license,
            skill_uri=f"skill://{self.skill_id}/SKILL.md",
            deprecated=self.deprecated,
            replaced_by=self.replaced_by,
        )

    def to_body(self) -> SkillBody:
        return SkillBody(
            skill_id=self.skill_id,
            instructions=self.instructions,
            system_prompt_addition=self.system_prompt_addition,
            example_usage=self.example_usage,
        )

    def to_options(self) -> SkillOptions:
        return SkillOptions(
            skill_id=self.skill_id,
            config_schema=self.config_schema,
            variants=self.variants,
            dependencies=self.dependencies,
            limitations=self.limitations,
        )


class SearchResponse(BaseModel):
    """What skills_find_relevant returns to the agent."""

    query: str
    results: list[SkillFrontMatter]
    total_found: int
