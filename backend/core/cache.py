from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from core.config import settings

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None


class SimpleTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        value = self._store.get(key)
        if value is None:
            return None
        payload, expires_at = value
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload: Any, ttl_seconds: int) -> None:
        self._store[key] = (payload, time.time() + ttl_seconds)


@dataclass(frozen=True)
class CacheHealth:
    backend: str
    available: bool


class CacheBackend:
    def __init__(self) -> None:
        self._memory = SimpleTTLCache()
        self._redis_client = None
        if settings.cache_url and redis is not None:
            try:
                self._redis_client = redis.Redis.from_url(settings.cache_url, decode_responses=True)
                self._redis_client.ping()
            except Exception:
                self._redis_client = None

    def _key(self, key: str) -> str:
        return f"{settings.cache_namespace}:{key}"

    def get(self, key: str) -> Any | None:
        cache_key = self._key(key)
        if self._redis_client is not None:
            try:
                payload = self._redis_client.get(cache_key)
                if payload is not None:
                    return json.loads(payload)
            except Exception:
                pass
        return self._memory.get(cache_key)

    def set(self, key: str, payload: Any, ttl_seconds: int) -> None:
        cache_key = self._key(key)
        if self._redis_client is not None:
            try:
                self._redis_client.setex(cache_key, ttl_seconds, json.dumps(payload))
            except Exception:
                self._memory.set(cache_key, payload, ttl_seconds)
                return
        self._memory.set(cache_key, payload, ttl_seconds)

    def health(self) -> CacheHealth:
        if self._redis_client is not None:
            try:
                self._redis_client.ping()
                return CacheHealth(backend="redis", available=True)
            except Exception:
                return CacheHealth(backend="hybrid-memory-fallback", available=True)
        return CacheHealth(backend="memory", available=True)
