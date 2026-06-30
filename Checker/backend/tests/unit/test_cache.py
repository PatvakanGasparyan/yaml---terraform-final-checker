"""Tests for validation result cache."""

from app.cache.validation_cache import ValidationCache, build_cache_key


def test_cache_hit_and_miss() -> None:
    cache = ValidationCache(max_size=10, ttl_seconds=60)
    key = build_cache_key("content", "a.yaml", "yaml", False, True, False)
    assert cache.get(key) is None
    cache.set(key, {"status": "success"})
    assert cache.get(key) == {"status": "success"}


def test_cache_eviction() -> None:
    cache = ValidationCache(max_size=2, ttl_seconds=60)
    for i in range(3):
        key = build_cache_key(f"c{i}", "f.yaml", "yaml", False, True, False)
        cache.set(key, {"i": i})
    assert cache.get(build_cache_key("c0", "f.yaml", "yaml", False, True, False)) is None
