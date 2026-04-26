"""MCP tool: skills_get_asset — fetch a template or static resource bundled with a skill.

Assets live in the skill's assets/ subdirectory. They are templates, output format
specifications, config examples, or other static resources the agent uses to structure
its output or as starting points for content generation.

Two modes:
  1. List mode (filename omitted or "list"): returns metadata for all assets.
  2. Fetch mode (filename provided): returns the full content of that asset.
"""

from __future__ import annotations

import json
import os

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_asset_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)


def get_skill_asset(skill_id: str, filename: str = "list") -> str:
    """Fetch a template or static resource bundled with a skill.

    Call this when the skill body instructions say "use assets/report-template.md"
    or similar. Assets are typically output format templates that the agent should
    populate with generated content.

    Args:
        skill_id: The skill_id returned by skills_find_relevant.
        filename: The asset filename to fetch (e.g. "report-template.md").
                  Pass "list" or omit to get a manifest of all asset files.

    Returns:
        JSON string.
        - List mode: {"skill_id": ..., "assets": [{filename, asset_type, description, file_path}, ...]}
        - Fetch mode: {"skill_id": ..., "filename": ..., "asset_type": ..., "description": ..., "content": ...}
        - Error: {"error": "..."}
    """
    # ── List mode ─────────────────────────────────────────────────────────────

    if filename in ("list", "", "all"):
        cache_key = f"asset_list|{skill_id}"
        cached = _asset_cache.get(cache_key)
        if cached is not None:
            return cached

        payloads = qdrant_manager.get_assets_for_skill(skill_id)
        assets = [
            {
                "filename": p.get("filename", ""),
                "asset_type": p.get("asset_type", "other"),
                "description": p.get("description", ""),
                "file_path": p.get("file_path", ""),
            }
            for p in payloads
        ]
        assets.sort(key=lambda a: a["filename"])

        result = json.dumps(
            {
                "skill_id": skill_id,
                "total": len(assets),
                "assets": assets,
            },
            indent=2,
        )
        _asset_cache.set(cache_key, result)
        return result

    # ── Fetch mode ────────────────────────────────────────────────────────────

    cache_key = f"asset|{skill_id}|{filename}"
    cached = _asset_cache.get(cache_key)
    if cached is not None:
        return cached

    payload = qdrant_manager.get_asset(skill_id, filename)
    if payload is None:
        all_assets = qdrant_manager.get_assets_for_skill(skill_id)
        all_filenames = [p.get("filename", "") for p in all_assets]
        # Case-insensitive fallback
        match = next(
            (f for f in all_filenames if f.lower() == filename.lower()), None
        )
        if match and match != filename:
            payload = qdrant_manager.get_asset(skill_id, match)
        if payload is None:
            return json.dumps(
                {
                    "error": (
                        f"Asset '{filename}' not found for skill '{skill_id}'. "
                        f"Call skills_get_asset(skill_id='{skill_id}', filename='list') "
                        f"to see available assets."
                    ),
                    "available": all_filenames,
                }
            )

    result = json.dumps(
        {
            "skill_id": payload.get("skill_id", skill_id),
            "skill_name": payload.get("skill_name", ""),
            "filename": payload.get("filename", filename),
            "file_path": payload.get("file_path", ""),
            "asset_type": payload.get("asset_type", "other"),
            "description": payload.get("description", ""),
            "content": payload.get("content", ""),
        },
        indent=2,
    )
    _asset_cache.set(cache_key, result)
    return result
