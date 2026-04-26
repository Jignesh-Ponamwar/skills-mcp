"""MCP tool: skills_get_reference — fetch a reference file bundled with a skill.

Reference files live in the skill's references/ subdirectory (e.g., FORMS.md, POLICY.md).
They are referenced in skill body instructions to provide supplementary documentation
without bloating the instructions text itself.

Two modes:
  1. List mode (filename omitted or "list"): returns metadata for all reference files
     so the agent can choose which to load.
  2. Fetch mode (filename provided): returns the full markdown content of that file.
"""

from __future__ import annotations

import json
import os

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_ref_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)


def get_skill_reference(skill_id: str, filename: str = "list") -> str:
    """Fetch a reference documentation file bundled with a skill.

    Call this when the skill body instructions say "see references/FORMS.md"
    or similar. In list mode, returns an index of all available reference files
    for a skill so you can choose which one to load.

    Args:
        skill_id: The skill_id returned by skills_find_relevant.
        filename: The reference filename to fetch (e.g. "FORMS.md", "POLICY.md").
                  Pass "list" or omit to get a manifest of all reference files.

    Returns:
        JSON string.
        - List mode: {"skill_id": ..., "references": [{filename, description, file_path}, ...]}
        - Fetch mode: {"skill_id": ..., "filename": ..., "description": ..., "content": ...}
        - Error: {"error": "..."}
    """
    # ── List mode ─────────────────────────────────────────────────────────────

    if filename in ("list", "", "all"):
        cache_key = f"ref_list|{skill_id}"
        cached = _ref_cache.get(cache_key)
        if cached is not None:
            return cached

        payloads = qdrant_manager.get_references_for_skill(skill_id)
        references = [
            {
                "filename": p.get("filename", ""),
                "description": p.get("description", ""),
                "file_path": p.get("file_path", ""),
            }
            for p in payloads
        ]
        # Sort alphabetically for deterministic output
        references.sort(key=lambda r: r["filename"])

        result = json.dumps(
            {
                "skill_id": skill_id,
                "total": len(references),
                "references": references,
            },
            indent=2,
        )
        _ref_cache.set(cache_key, result)
        return result

    # ── Fetch mode ────────────────────────────────────────────────────────────

    cache_key = f"ref|{skill_id}|{filename}"
    cached = _ref_cache.get(cache_key)
    if cached is not None:
        return cached

    payload = qdrant_manager.get_reference(skill_id, filename)
    if payload is None:
        # Try a case-insensitive match by listing all references
        all_refs = qdrant_manager.get_references_for_skill(skill_id)
        all_filenames = [p.get("filename", "") for p in all_refs]
        match = next(
            (f for f in all_filenames if f.lower() == filename.lower()), None
        )
        if match and match != filename:
            # Retry with correct casing
            payload = qdrant_manager.get_reference(skill_id, match)
        if payload is None:
            return json.dumps(
                {
                    "error": (
                        f"Reference '{filename}' not found for skill '{skill_id}'. "
                        f"Call skills_get_reference(skill_id='{skill_id}', filename='list') "
                        f"to see available reference files."
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
            "description": payload.get("description", ""),
            "content": payload.get("content", ""),
        },
        indent=2,
    )
    _ref_cache.set(cache_key, result)
    return result
