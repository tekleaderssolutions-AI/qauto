"""Redis cache decorator for GET endpoints. Falls back to in-memory when Redis unavailable."""
import json
import functools
import hashlib
import time
from typing import Any, Callable

# In-memory fallback when Redis not available
_memory_cache: dict[str, tuple[Any, float]] = {}
_MEMORY_TTL = 300  # 5 min


def _cache_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.sha256(raw.encode()).hexdigest()


def cache(ttl: int = 300, key_prefix: str = "api"):
    """Cache decorator: Redis if available, else in-memory. Works with sync route handlers."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ckey = _cache_key(key_prefix + ":" + func.__name__, *args, **kwargs)
            # Try Redis first
            try:
                import redis
                r = redis.from_url(
                    __import__("os").environ.get("REDIS_URL", "redis://localhost:6379"),
                    decode_responses=True,
                )
                cached = r.get(ckey)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
            # Fallback: in-memory
            if ckey in _memory_cache:
                val, exp = _memory_cache[ckey]
                if time.time() < exp:
                    return val
                del _memory_cache[ckey]
            result = func(*args, **kwargs)
            def _serialize(obj):
                if hasattr(obj, "item"):
                    return obj.item()
                raise TypeError(type(obj).__name__)
            try:
                import redis
                r = redis.from_url(
                    __import__("os").environ.get("REDIS_URL", "redis://localhost:6379"),
                    decode_responses=True,
                )
                r.setex(ckey, ttl, json.dumps(result, default=lambda x: _serialize(x) if hasattr(x, "item") else str(x)))
            except Exception:
                _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))
            return result

        return wrapper

    return decorator
