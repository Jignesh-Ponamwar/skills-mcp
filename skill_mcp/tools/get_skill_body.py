"""MCP tool: skills_get_body — fetch full instructions for a single skill.

The response includes a tier3_manifest field listing available reference files,
scripts, and assets by filename only — no content is loaded. This lets the
agent selectively fetch only what the instructions reference (progressive
disclosure). If no tier-3 files exist for a skill the manifest is empty.

Version pinning: pass version="1.2" to pin to a specific skill version.
If the requested version is not found the latest version is returned with a
version_note field explaining the fallback.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from ..db.cache import TTLCache
from ..db.qdrant_manager import qdrant_manager

_body_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)


def get_skill_body(skill_id: str, version: Optional[str] = None) -> str:
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
                  May include an inline version suffix: "stripe-integration@1.2"
        version:  Optional version string (e.g. "1.2"). If provided and found,
                  the pinned version body is returned. If not found, the latest
                  version is returned with a version_note field.

    Returns:
        JSON string matching the SkillBody schema plus tier3_manifest field,
        or an error object if the skill_id is not found.
    """
    # Parse inline version suffix: "stripe-integration@1.2"
    if "@" in skill_id and version is None:
        skill_id, version = skill_id.rsplit("@", 1)

    cache_key = f"body|{skill_id}|{version or 'latest'}"
    cached = _body_cache.get(cache_key)
    if cached is not None:
        return cached

    version_note: Optional[str] = None
    actual_version: Optional[str] = None

    if version:
        body = qdrant_manager.get_body_versioned(skill_id, version)
        if body is None:
            # Requested version not found — fall back to latest
            body = qdrant_manager.get_body(skill_id)
            if body is not None:
                version_note = (
                    f"Requested version {version!r} not found in registry; "
                    f"returning latest version."
                )
        else:
            actual_version = version
    else:
        body = qdrant_manager.get_body(skill_id)

    if body is None:
        return json.dumps(
            {"error": f"skill_id '{skill_id}' not found in body collection"}
        )

    body_dict = body.model_dump()
    body_dict["tier3_manifest"] = qdrant_manager.get_tier3_manifest(skill_id)

    if version_note:
        body_dict["version_note"] = version_note
    if actual_version:
        body_dict["pinned_version"] = actual_version

    # Attach deprecation notice if the skill is marked deprecated in frontmatter.
    try:
        fm_payload = qdrant_manager.get_frontmatter_payload(skill_id)
        if fm_payload and fm_payload.get("deprecated"):
            replaced_by = fm_payload.get("replaced_by", "")
            msg = "This skill is deprecated."
            if replaced_by:
                msg += f" Use '{replaced_by}' instead."
            body_dict["deprecation_notice"] = msg
    except Exception:
        pass

    result = json.dumps(body_dict, indent=2)
    _body_cache.set(cache_key, result)
    return result
