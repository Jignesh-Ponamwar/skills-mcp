"""Qdrant connection, collection bootstrap, and query helpers.

Six collections across three disclosure tiers:
  skill_frontmatter  — 384-dim vectors, semantic search
  skill_body         — payload-only, full instructions
  skill_options      — payload-only, config schema, variants, dependencies
  skill_references   — payload-only, reference markdown files
  skill_scripts      — payload-only, executable scripts (source never returned to agents)
  skill_assets       — payload-only, templates and static resources
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from ..models.skill import (
    SkillAsset,
    SkillBody,
    SkillFrontMatter,
    SkillOptions,
    SkillReference,
    SkillScript,
)

# Collection names — override via env vars if you renamed them in Qdrant
FRONTMATTER_COLLECTION = os.getenv("FRONTMATTER_COLLECTION", "skill_frontmatter")
BODY_COLLECTION = os.getenv("BODY_COLLECTION", "skill_body")
OPTIONS_COLLECTION = os.getenv("OPTIONS_COLLECTION", "skill_options")
REFERENCES_COLLECTION = os.getenv("REFERENCES_COLLECTION", "skill_references")
SCRIPTS_COLLECTION = os.getenv("SCRIPTS_COLLECTION", "skill_scripts")
ASSETS_COLLECTION = os.getenv("ASSETS_COLLECTION", "skill_assets")

_VECTOR_DIM = 384
_DUMMY_VEC = [0.0]  # 1-dim placeholder for payload-only collections


def _skill_uuid(key: str) -> str:
    """Deterministic UUID from a string key so re-seeding is idempotent."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


class QdrantManager:
    def __init__(self) -> None:
        self._client: Optional[QdrantClient] = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        self._client = QdrantClient(url=url, api_key=api_key)

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            raise RuntimeError(
                "QdrantManager not connected — call qdrant_manager.connect() first"
            )
        return self._client

    # ── Collection bootstrap ──────────────────────────────────────────────────

    def ensure_collections(self) -> None:
        """Create all six collections if they don't exist; safe to call repeatedly."""
        existing = {c.name for c in self.client.get_collections().collections}

        # ── Tier-1: frontmatter (384-dim vector for semantic search) ──────────

        if FRONTMATTER_COLLECTION not in existing:
            self.client.create_collection(
                collection_name=FRONTMATTER_COLLECTION,
                vectors_config=VectorParams(
                    size=_VECTOR_DIM,
                    distance=Distance.COSINE,
                    on_disk=False,
                ),
            )
            self.client.create_payload_index(
                collection_name=FRONTMATTER_COLLECTION,
                field_name="skill_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )

        # ── Tier-2: body + options (payload-only) ─────────────────────────────

        for col in (BODY_COLLECTION, OPTIONS_COLLECTION):
            if col not in existing:
                self.client.create_collection(
                    collection_name=col,
                    vectors_config=VectorParams(size=1, distance=Distance.COSINE),
                )
                self.client.create_payload_index(
                    collection_name=col,
                    field_name="skill_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )

        # ── Tier-3: references, scripts, assets (payload-only, skill_id+filename lookup) ──

        for col in (REFERENCES_COLLECTION, SCRIPTS_COLLECTION, ASSETS_COLLECTION):
            if col not in existing:
                self.client.create_collection(
                    collection_name=col,
                    vectors_config=VectorParams(size=1, distance=Distance.COSINE),
                )
                # Index both skill_id and filename for compound lookups
                self.client.create_payload_index(
                    collection_name=col,
                    field_name="skill_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=col,
                    field_name="filename",
                    field_schema=PayloadSchemaType.KEYWORD,
                )

    # ── Upsert helpers ────────────────────────────────────────────────────────

    def upsert_frontmatter(
        self, frontmatter: SkillFrontMatter, vector: list[float]
    ) -> None:
        point = PointStruct(
            id=_skill_uuid(frontmatter.skill_id),
            vector=vector,
            payload=frontmatter.model_dump(exclude={"score"}),
        )
        self.client.upsert(collection_name=FRONTMATTER_COLLECTION, points=[point])

    def upsert_body(self, body: SkillBody) -> None:
        point = PointStruct(
            id=_skill_uuid(f"body:{body.skill_id}"),
            vector=_DUMMY_VEC,
            payload=body.model_dump(),
        )
        self.client.upsert(collection_name=BODY_COLLECTION, points=[point])

    def upsert_options(self, options: SkillOptions) -> None:
        point = PointStruct(
            id=_skill_uuid(f"options:{options.skill_id}"),
            vector=_DUMMY_VEC,
            payload=options.model_dump(),
        )
        self.client.upsert(collection_name=OPTIONS_COLLECTION, points=[point])

    def upsert_many_frontmatter(
        self, pairs: list[tuple[SkillFrontMatter, list[float]]]
    ) -> None:
        points = [
            PointStruct(
                id=_skill_uuid(fm.skill_id),
                vector=vec,
                payload=fm.model_dump(exclude={"score"}),
            )
            for fm, vec in pairs
        ]
        self.client.upsert(collection_name=FRONTMATTER_COLLECTION, points=points)

    def upsert_many_body(self, bodies: list[SkillBody]) -> None:
        points = [
            PointStruct(
                id=_skill_uuid(f"body:{b.skill_id}"),
                vector=_DUMMY_VEC,
                payload=b.model_dump(),
            )
            for b in bodies
        ]
        self.client.upsert(collection_name=BODY_COLLECTION, points=points)

    def upsert_many_options(self, options_list: list[SkillOptions]) -> None:
        points = [
            PointStruct(
                id=_skill_uuid(f"options:{o.skill_id}"),
                vector=_DUMMY_VEC,
                payload=o.model_dump(),
            )
            for o in options_list
        ]
        self.client.upsert(collection_name=OPTIONS_COLLECTION, points=points)

    def upsert_reference(self, ref: SkillReference) -> None:
        """Upsert a reference markdown file for a skill."""
        point = PointStruct(
            id=_skill_uuid(f"ref:{ref.skill_id}:{ref.filename}"),
            vector=_DUMMY_VEC,
            payload=ref.model_dump(),
        )
        self.client.upsert(collection_name=REFERENCES_COLLECTION, points=[point])

    def upsert_script(self, script: SkillScript) -> None:
        """Upsert an executable script for a skill (source stored internally)."""
        point = PointStruct(
            id=_skill_uuid(f"script:{script.skill_id}:{script.filename}"),
            vector=_DUMMY_VEC,
            payload=script.model_dump(),
        )
        self.client.upsert(collection_name=SCRIPTS_COLLECTION, points=[point])

    def upsert_asset(self, asset: SkillAsset) -> None:
        """Upsert a template or static resource for a skill."""
        point = PointStruct(
            id=_skill_uuid(f"asset:{asset.skill_id}:{asset.filename}"),
            vector=_DUMMY_VEC,
            payload=asset.model_dump(),
        )
        self.client.upsert(collection_name=ASSETS_COLLECTION, points=[point])

    # ── Query helpers ─────────────────────────────────────────────────────────

    def search_frontmatter(
        self, query_vector: list[float], top_k: int = 5, score_threshold: float = 0.0
    ) -> list[SkillFrontMatter]:
        response = self.client.query_points(
            collection_name=FRONTMATTER_COLLECTION,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        hits = response.points
        results: list[SkillFrontMatter] = []
        for hit in hits:
            payload: dict[str, Any] = hit.payload or {}
            payload["score"] = hit.score
            results.append(SkillFrontMatter(**payload))
        return results

    def _payload_lookup(
        self, collection_name: str, skill_id: str
    ) -> Optional[dict[str, Any]]:
        """Look up a single payload by skill_id."""
        points, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="skill_id", match=MatchValue(value=skill_id)
                    )
                ]
            ),
            with_payload=True,
            limit=1,
        )
        if not points:
            return None
        return points[0].payload  # type: ignore[return-value]

    def get_body(self, skill_id: str) -> Optional[SkillBody]:
        payload = self._payload_lookup(BODY_COLLECTION, skill_id)
        return SkillBody(**payload) if payload else None

    def get_options(self, skill_id: str) -> Optional[SkillOptions]:
        payload = self._payload_lookup(OPTIONS_COLLECTION, skill_id)
        return SkillOptions(**payload) if payload else None

    def _payload_list_by_skill(
        self, collection_name: str, skill_id: str
    ) -> list[dict[str, Any]]:
        """Return all payloads for a given skill_id from a collection."""
        points, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="skill_id", match=MatchValue(value=skill_id)
                    )
                ]
            ),
            with_payload=True,
            limit=100,  # no skill should have >100 files per tier
        )
        return [p.payload for p in points if p.payload]  # type: ignore[misc]

    def _payload_lookup_by_file(
        self, collection_name: str, skill_id: str, filename: str
    ) -> Optional[dict[str, Any]]:
        """Look up a single file payload by skill_id + filename compound key."""
        points, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="skill_id", match=MatchValue(value=skill_id)
                    ),
                    FieldCondition(
                        key="filename", match=MatchValue(value=filename)
                    ),
                ]
            ),
            with_payload=True,
            limit=1,
        )
        return points[0].payload if points else None  # type: ignore[return-value]

    def get_references_for_skill(self, skill_id: str) -> list[dict[str, Any]]:
        """List all reference files for a skill (metadata only, not content filtered here)."""
        return self._payload_list_by_skill(REFERENCES_COLLECTION, skill_id)

    def get_reference(
        self, skill_id: str, filename: str
    ) -> Optional[dict[str, Any]]:
        """Fetch a specific reference file by skill_id + filename."""
        return self._payload_lookup_by_file(REFERENCES_COLLECTION, skill_id, filename)

    def get_scripts_for_skill(self, skill_id: str) -> list[dict[str, Any]]:
        """List all scripts for a skill."""
        return self._payload_list_by_skill(SCRIPTS_COLLECTION, skill_id)

    def get_script(self, skill_id: str, filename: str) -> Optional[dict[str, Any]]:
        """Fetch a specific script by skill_id + filename (includes source for execution)."""
        return self._payload_lookup_by_file(SCRIPTS_COLLECTION, skill_id, filename)

    def get_assets_for_skill(self, skill_id: str) -> list[dict[str, Any]]:
        """List all assets for a skill."""
        return self._payload_list_by_skill(ASSETS_COLLECTION, skill_id)

    def get_asset(self, skill_id: str, filename: str) -> Optional[dict[str, Any]]:
        """Fetch a specific asset by skill_id + filename."""
        return self._payload_lookup_by_file(ASSETS_COLLECTION, skill_id, filename)

    def get_tier3_manifest(self, skill_id: str) -> dict[str, list[str]]:
        """Return just filenames from all three tier-3 collections for a skill.

        Gracefully returns empty lists if a collection doesn't exist yet (e.g.,
        seeder hasn't run) or if any other error occurs. Never raises.
        """

        def _safe_filenames(collection: str) -> list[str]:
            try:
                payloads = self._payload_list_by_skill(collection, skill_id)
                return sorted(
                    p["filename"] for p in payloads if "filename" in p
                )
            except Exception:
                return []

        return {
            "references": _safe_filenames(REFERENCES_COLLECTION),
            "scripts": _safe_filenames(SCRIPTS_COLLECTION),
            "assets": _safe_filenames(ASSETS_COLLECTION),
        }


# Module-level singleton
qdrant_manager = QdrantManager()
