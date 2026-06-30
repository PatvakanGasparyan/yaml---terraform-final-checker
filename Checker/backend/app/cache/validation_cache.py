"""
In-memory LRU cache for validation results keyed by content hash.

Avoids re-running expensive scans on identical input within TTL window.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class CacheKey:
    """Unique key for a validation request."""

    content_hash: str
    file_path: str
    validation_type: str
    include_ai: bool
    include_security: bool
    auto_fix: bool


def build_cache_key(
    content: str,
    file_path: str,
    validation_type: str,
    include_ai: bool,
    include_security: bool,
    auto_fix: bool,
) -> CacheKey:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return CacheKey(digest, file_path, validation_type, include_ai, include_security, auto_fix)


@dataclass
class CacheEntry:
    value: dict[str, Any]
    expires_at: float


class ValidationCache:
    """Thread-safe-ish LRU cache with TTL (single-process)."""

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    def _key_str(self, key: CacheKey) -> str:
        return json.dumps(
            {
                "h": key.content_hash,
                "p": key.file_path,
                "t": key.validation_type,
                "ai": key.include_ai,
                "sec": key.include_security,
                "fix": key.auto_fix,
            },
            sort_keys=True,
        )

    def get(self, key: CacheKey) -> dict[str, Any] | None:
        k = self._key_str(key)
        entry = self._store.get(k)
        if not entry:
            return None
        if time.time() > entry.expires_at:
            del self._store[k]
            return None
        self._store.move_to_end(k)
        return entry.value

    def set(self, key: CacheKey, value: dict[str, Any]) -> None:
        k = self._key_str(key)
        if k in self._store:
            del self._store[k]
        while len(self._store) >= self.max_size:
            self._store.popitem(last=False)
        self._store[k] = CacheEntry(value=value, expires_at=time.time() + self.ttl_seconds)

    def clear(self) -> None:
        self._store.clear()


@lru_cache
def get_validation_cache() -> ValidationCache:
    from app.core.config import get_settings

    s = get_settings()
    return ValidationCache(max_size=s.VALIDATION_CACHE_MAX_SIZE, ttl_seconds=s.VALIDATION_CACHE_TTL)
