"""Cache decorator for GET endpoints. Uses Redis when REDIS_URL is set, else in-memory (no Redis needed)."""
import json
import functools
import hashlib
import os
import time
from typing import Any, Callable

# In-memory fallback when Redis not available (e.g. Render free tier with 1 DB only)
_memory_cache: dict[str, tuple[Any, float]] = {}
_MEMORY_TTL = 3600  # 1 hour

_redis_available: bool | None = None


def _has_redis() -> bool:
    """Use Redis only if REDIS_URL is set. On Render free tier (no Redis), leave unset to use in-memory."""
    global _redis_available
    if _redis_available is not None:
        return _redis_available
    url = os.environ.get("REDIS_URL", "").strip()
    _redis_available = bool(url)
    return _redis_available


def _cache_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.sha256(raw.encode()).hexdigest()


def cache(ttl: int = 300, key_prefix: str = "api"):
    """Cache decorator: Redis if REDIS_URL set, else in-memory. Works with sync route handlers."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ckey = _cache_key(key_prefix + ":" + func.__name__, *args, **kwargs)
            # Redis when available (production with Redis)
            if _has_redis():
                try:
                    import redis
                    r = redis.from_url(
                        os.environ.get("REDIS_URL", ""),
                        decode_responses=True,
                        socket_connect_timeout=2,
                    )
                    cached = r.get(ckey)
                    if cached:
                        return json.loads(cached)
                except Exception:
                    pass
            # In-memory (default on Render free tier / no Redis)
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

            if _has_redis():
                try:
                    import redis
                    r = redis.from_url(
                        os.environ.get("REDIS_URL", ""),
                        decode_responses=True,
                        socket_connect_timeout=2,
                    )
                    r.setex(ckey, ttl, json.dumps(result, default=lambda x: _serialize(x) if hasattr(x, "item") else str(x)))
                except Exception:
                    _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))
            else:
                _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))
            return result

        return wrapper

    return decorator
