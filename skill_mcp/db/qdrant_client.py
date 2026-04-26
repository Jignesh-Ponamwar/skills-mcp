"""
Qdrant Cloud client factory.

Reads QDRANT_URL and QDRANT_API_KEY from the environment and returns a
configured QdrantClient instance ready for use with Qdrant Cloud.
"""

from __future__ import annotations

import os

from qdrant_client import QdrantClient


def get_qdrant_client() -> QdrantClient:
    """Create a QdrantClient pointed at Qdrant Cloud (or local if URL is localhost)."""
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    return QdrantClient(url=url, api_key=api_key)
