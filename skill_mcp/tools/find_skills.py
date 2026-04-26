"""MCP tool: skills_find_relevant — semantic search over the frontmatter collection."""

from __future__ import annotations

import os

from ..db.cache import TTLCache
from ..db.embedder import embedder
from ..db.qdrant_manager import qdrant_manager
from ..models.skill import SearchResponse

_search_cache: TTLCache = TTLCache(
    ttl=float(os.getenv("CACHE_TTL_SECONDS", "300")),
    max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
)

_DEFAULT_TOP_K = 5
_MAX_TOP_K = 20
_MAX_QUERY_LEN = 2_000  # chars — prevent cache bloat and oversized embedding payloads


def find_relevant_skills(query: str, top_k: int = _DEFAULT_TOP_K) -> str:
    """
    Find skills relevant to *query* via semantic vector search.

    Returns a JSON string containing ranked SkillFrontMatter objects with
    similarity scores. Call skills_get_body for full instructions on any
    returned skill_id.

    Args:
        query:  Natural language description of what the agent needs to do.
        top_k:  Number of results to return (1-20, default 5).

    Returns:
        JSON string matching the SearchResponse schema.
    """
    import json as _json

    query = str(query).strip()
    if not query:
        return _json.dumps({"error": "query must not be empty"})
    if len(query) > _MAX_QUERY_LEN:
        return _json.dumps(
            {"error": f"query exceeds maximum length of {_MAX_QUERY_LEN} characters"}
        )

    top_k = max(1, min(top_k, _MAX_TOP_K))
    # Use only the first 200 chars of the query in the cache key to bound key size;
    # the full query is still used for embedding — this just limits key memory usage.
    cache_key = f"search|{top_k}|{query[:200]}"

    cached = _search_cache.get(cache_key)
    if cached is not None:
        return cached

    vector = embedder.embed(query)
    frontmatters = qdrant_manager.search_frontmatter(vector, top_k=top_k)

    response = SearchResponse(
        query=query,
        results=frontmatters,
        total_found=len(frontmatters),
    )
    result = response.model_dump_json(indent=2)
    _search_cache.set(cache_key, result)
    return result
