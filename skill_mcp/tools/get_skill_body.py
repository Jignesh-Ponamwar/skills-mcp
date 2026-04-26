"""MCP tool: skills_get_body — fetch full instructions for a single skill.

The response includes a tier3_manifest field listing available reference files,
scripts, and assets by filename only — no content is loaded. This lets the
agent selectively fetch only what the instructions reference (progressive
disclosure). If no tier-3 files exist for a skill the manifest is empty.
"""

from __future__ import annotations

import json
import os

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_body_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)


def get_skill_body(skill_id: str) -> str:
    """Retrieve the full body (instructions + system prompt addition) for a skill.

    Call this after skills_find_relevant once you have decided which skill to
    activate. The body contains step-by-step instructions and any system-prompt
    text the agent should prepend for this skill.

    The response also includes tier3_manifest — a lightweight index of available
    reference files, scripts, and assets. Check it and load what you need:
      - references: call skills_get_reference(skill_id, filename)
      - scripts: call skills_run_script(skill_id, filename, input_data)
      - assets: call skills_get_asset(skill_id, filename)

    Args:
        skill_id: The skill_id string returned by skills_find_relevant.

    Returns:
        JSON string matching the SkillBody schema plus tier3_manifest field,
        or an error object if the skill_id is not found.
    """
    cache_key = f"body|{skill_id}"
    cached = _body_cache.get(cache_key)
    if cached is not None:
        return cached

    body = qdrant_manager.get_body(skill_id)
    if body is None:
        return json.dumps(
            {"error": f"skill_id '{skill_id}' not found in body collection"}
        )

    body_dict = body.model_dump()
    body_dict["tier3_manifest"] = qdrant_manager.get_tier3_manifest(skill_id)

    result = json.dumps(body_dict, indent=2)
    _body_cache.set(cache_key, result)
    return result
