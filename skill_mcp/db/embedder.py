"""Cloudflare Workers AI embedding client with TTL cache.

Uses @cf/baai/bge-small-en-v1.5 (384-dim) via the Cloudflare REST API —
the same model the deployed Worker uses at query time, so local-server
vectors and Worker query vectors are directly comparable.

Required env vars (.env):
  WORKERS_AI_ACCOUNT_ID — Cloudflare account ID
  WORKERS_AI_API_TOKEN  — Cloudflare API token with "Workers AI Run" permission
"""

from __future__ import annotations

import os

import requests

from .cache import TTLCache

_CACHE_TTL = float(os.getenv("CACHE_TTL_SECONDS", "300"))
_CACHE_MAX = int(os.getenv("CACHE_MAX_SIZE", "1000"))
_MODEL = "@cf/baai/bge-small-en-v1.5"

DIMENSION = 384


class Embedder:
    """Cloudflare Workers AI embedding client with TTL cache."""

    DIMENSION: int = DIMENSION

    def __init__(self) -> None:
        self._cache: TTLCache = TTLCache(ttl=_CACHE_TTL, max_size=_CACHE_MAX)

    # ── Public API ─────────────────────────────────────────────────────────────

    def load(self) -> None:
        """No-op — Workers AI needs no local model loading."""

    @property
    def is_loaded(self) -> bool:
        """Always True — Workers AI is a remote API, no local model to warm up."""
        return True

    def embed(self, text: str) -> list[float]:
        """Embed a single text string, with TTL cache."""
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        vec = self._call_api_batch([text])[0]
        self._cache.set(text, vec)
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single Workers AI API call (cache-aware).

        Texts already in cache are served immediately; only uncached texts are
        sent to the API in one round-trip, then results are merged back in order.
        """
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            cached = self._cache.get(text)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            vectors = self._call_api_batch(uncached_texts)
            for idx, vec in zip(uncached_indices, vectors):
                self._cache.set(texts[idx], vec)
                results[idx] = vec

        return results  # type: ignore[return-value]  # all slots filled above

    # ── Internal ───────────────────────────────────────────────────────────────

    def _call_api_batch(self, texts: list[str]) -> list[list[float]]:
        """Send texts to Workers AI in one HTTP round-trip, return all vectors."""
        account_id = os.getenv("WORKERS_AI_ACCOUNT_ID", "")
        api_token = os.getenv("WORKERS_AI_API_TOKEN", "")

        if not account_id or not api_token:
            raise RuntimeError(
                "WORKERS_AI_ACCOUNT_ID and WORKERS_AI_API_TOKEN must be set in .env.\n"
                "Get them at https://dash.cloudflare.com — "
                "token needs 'Workers AI Run' permission."
            )

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            f"/ai/run/{_MODEL}"
        )
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_token}"},
            json={"text": texts},
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        if not result.get("success"):
            # Do not include the raw API response — it may contain account details or tokens.
            errors = result.get("errors") or []
            msg = "; ".join(str(e.get("message", e)) for e in errors) if errors else "unknown error"
            raise RuntimeError(f"Workers AI embedding failed: {msg}")
        vectors: list[list[float]] = result["result"]["data"]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Workers AI returned {len(vectors)} vectors for {len(texts)} texts"
            )
        return vectors


# Module-level singleton used by find_skills.py and the local server
embedder = Embedder()
