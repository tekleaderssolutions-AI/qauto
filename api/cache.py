"""
Cache decorator for GET endpoints.
- Uses Redis (with TLS support for Upstash rediss://) when REDIS_URL is set.
- Falls back to in-memory cache when Redis is unavailable.
- Singleton Redis client (one connection pool, not a new conn per request).
- Error logging so failures are visible in Render logs.
"""
import json
import functools
import hashlib
import logging
import os
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------
_memory_cache: dict[str, tuple[Any, float]] = {}
_MEMORY_TTL = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Singleton Redis client — created once, reused across all requests
# ---------------------------------------------------------------------------
_redis_client = None
_redis_checked = False


def _get_redis():
    """
    Return a singleton Redis client configured for Upstash (rediss:// TLS).
    Returns None if REDIS_URL is not set or connection fails.
    """
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    _redis_checked = True
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        logger.info("[cache] REDIS_URL not set — using in-memory cache.")
        return None

    try:
        import redis as redis_lib

        _redis_client = redis_lib.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            # Required for Upstash rediss:// (TLS with self-signed cert)
            ssl_cert_reqs=None,
        )
        # Verify connection on startup
        _redis_client.ping()
        logger.info("[cache] ✅ Redis connected: %s", url.split("@")[-1])
    except Exception as exc:
        logger.warning("[cache] ⚠️ Redis connection failed (%s) — falling back to in-memory.", exc)
        _redis_client = None

    return _redis_client


# ---------------------------------------------------------------------------
# Cache key helper
# ---------------------------------------------------------------------------
def _cache_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Cache decorator
# ---------------------------------------------------------------------------
def cache(ttl: int = 300, key_prefix: str = "api"):
    """
    Decorator that caches sync route handler results.
    Uses Redis (with Upstash TLS fix) when available, in-memory otherwise.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ckey = _cache_key(key_prefix + ":" + func.__name__, *args, **kwargs)
            r = _get_redis()

            # --- Try Redis first ---
            if r is not None:
                try:
                    cached = r.get(ckey)
                    if cached:
                        return json.loads(cached)
                except Exception as exc:
                    logger.warning("[cache] Redis GET failed for %s: %s", func.__name__, exc)

            # --- Try in-memory fallback ---
            if ckey in _memory_cache:
                val, exp = _memory_cache[ckey]
                if time.time() < exp:
                    return val
                del _memory_cache[ckey]

            # --- Execute the actual function ---
            result = func(*args, **kwargs)

            def _serialize(obj):
                if hasattr(obj, "item"):
                    return obj.item()
                raise TypeError(type(obj).__name__)

            serialized = json.dumps(
                result,
                default=lambda x: _serialize(x) if hasattr(x, "item") else str(x),
            )

            # --- Store in Redis ---
            if r is not None:
                try:
                    r.setex(ckey, ttl, serialized)
                except Exception as exc:
                    logger.warning("[cache] Redis SET failed for %s: %s — falling back to memory.", func.__name__, exc)
                    _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))
            else:
                # Fallback: in-memory
                _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))

            return result

        return wrapper

    return decorator
