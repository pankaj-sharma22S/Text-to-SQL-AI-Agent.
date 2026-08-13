import hashlib
import time
from typing import Any

class ResponseCache:
    def __init__(self, redis_url=None, ttl_seconds=300):
        self.ttl_seconds = ttl_seconds
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis = None
        if redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    @staticmethod
    def key(provider: str, prompt: str) -> str:
        return f"ai:{provider}:{hashlib.sha256(prompt.encode()).hexdigest()}"

    def get(self, key: str):
        if self._redis:
            return self._redis.get(key)
        item = self._memory.get(key)
        if not item or item[0] <= time.monotonic():
            self._memory.pop(key, None)
            return None
        return item[1]

    def set(self, key: str, value: str):
        if self._redis:
            self._redis.setex(key, self.ttl_seconds, value)
        else:
            self._memory[key] = (time.monotonic() + self.ttl_seconds, value)
