"""MCP tool: skills_get_options — fetch config variants and constraints for a skill."""

from __future__ import annotations

import json
import os

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_options_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)


def get_skill_options(skill_id: str) -> str:
    """
    Retrieve configuration schema, variants, dependencies, and limitations for a skill.

    This is an optional deep-dive call. Use it when you need to know available
    config options (e.g., which output format variants exist) or to check
    hard limitations before starting a task.

    Args:
        skill_id:  The skill_id string returned by skills_find_relevant.

    Returns:
        JSON string matching the SkillOptions schema, or an error object if
        the skill_id is not found.
    """
    cache_key = f"options|{skill_id}"
    cached = _options_cache.get(cache_key)
    if cached is not None:
        return cached

    options = qdrant_manager.get_options(skill_id)
    if options is None:
        return json.dumps(
            {"error": f"skill_id '{skill_id}' not found in options collection"}
        )

    result = options.model_dump_json(indent=2)
    _options_cache.set(cache_key, result)
    return result
