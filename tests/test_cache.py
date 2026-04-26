"""Unit tests for TTLCache — no external deps required."""

import time

import pytest

from skill_mcp.db.cache import TTLCache


def test_set_and_get():
    cache = TTLCache(ttl=60)
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_miss_returns_none():
    cache = TTLCache(ttl=60)
    assert cache.get("nonexistent") is None


def test_expired_entry_returns_none():
    cache = TTLCache(ttl=60)
    cache.set("k", "v")
    # Force expiry by backdating the stored timestamp
    value, _ = cache._store["k"]
    cache._store["k"] = (value, time.monotonic() - 1)
    assert cache.get("k") is None


def test_max_size_eviction():
    cache = TTLCache(ttl=60, max_size=3)
    for i in range(4):
        cache.set(str(i), i)
    assert len(cache) <= 3


def test_clear():
    cache = TTLCache(ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a") is None


def test_invalidate():
    cache = TTLCache(ttl=60)
    cache.set("x", 99)
    cache.invalidate("x")
    assert cache.get("x") is None


def test_overwrite():
    cache = TTLCache(ttl=60)
    cache.set("k", "first")
    cache.set("k", "second")
    assert cache.get("k") == "second"
