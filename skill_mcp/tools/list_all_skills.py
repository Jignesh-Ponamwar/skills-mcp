"""MCP tool: skills_list_all - browse the complete skill catalogue without search."""

from __future__ import annotations

import json as _json
import os

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_list_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=10,  # Cache a few pages of paginated results
)


def list_all_skills(limit: int = 100, offset: int = 0) -> str:
    """
    Browse all skills in the registry without semantic search.

    Returns lightweight frontmatter for each skill to keep token usage reasonable.
    This is useful when you want to see what skills are available, understand the
    full breadth of the registry, or look for skills by browsing rather than
    semantic search.

    Args:
        limit:  Number of results to return (default 100, max 100).
        offset: Number of results to skip (for pagination, default 0).

    Returns:
        JSON string with {total: int, skills: [SkillFrontMatter], count: int}
    """
    # Use simple cache key since pagination parameters change it
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    cache_key = f"list_all|{offset}|{limit}"
    cached = _list_cache.get(cache_key)
    if cached is not None:
        return cached

    # Query all frontmatters from Qdrant without vector search
    # This is a direct payload query, no embedding needed
    try:
        all_frontmatters = qdrant_manager.list_all_frontmatter(offset=offset, limit=limit)
        total_count = qdrant_manager.get_frontmatter_count()
    except Exception:  # noqa: BLE001
        return _json.dumps(
            {
                "error": "Failed to retrieve skills from registry",
                "total": 0,
                "skills": [],
                "count": 0,
            }
        )

    response = {
        "workflow_warning": (
            "These skill_ids are for BROWSING ONLY and have NOT been scored for "
            "relevance to your current task. "
            "NEXT STEP: call skills_find_relevant(query='<your specific task>') to "
            "find the most relevant skill and get a similarity score. "
            "Do NOT pass any skill_id from this list directly to skills_get_body "
            "without first running skills_find_relevant (score > 0.6 required)."
        ),
        "total": total_count,
        "skills": [fm.model_dump() for fm in all_frontmatters],
        "count": len(all_frontmatters),
        "offset": offset,
        "limit": limit,
    }
    result = _json.dumps(response, indent=2)
    _list_cache.set(cache_key, result)
    return result
