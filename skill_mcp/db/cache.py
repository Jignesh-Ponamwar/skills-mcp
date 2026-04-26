"""Simple in-memory TTL cache — no external deps required."""

from __future__ import annotations

import threading
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl: float = 300.0, max_size: int = 1000) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self.max_size:
                self._evict_unsafe()
            self._store[key] = (value, time.monotonic() + self.ttl)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def _evict_unsafe(self) -> None:
        """Evict expired entries. Must be called with self._lock held."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if exp < now]
        for k in expired:
            del self._store[k]
        # If still at capacity, evict the single soonest-expiring entry
        if len(self._store) >= self.max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
