"""
Cache decorator for FastAPI GET endpoints.
- Primary: Upstash Redis REST API (HTTP/HTTPS) — works on ALL platforms including Render free tier.
  No TCP port issues. Uses UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN env vars.
- Secondary: Standard redis-py client (REDIS_URL) — used if REST env vars are not set.
- Fallback: In-memory cache — used if both Redis options fail.
- Singleton connections, error logging visible in Render logs.
"""
import json
import functools
import hashlib
import logging
import os
import ssl
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------
_memory_cache: dict[str, tuple[Any, float]] = {}
_MEMORY_TTL = 3600

# ---------------------------------------------------------------------------
# Upstash REST client (singleton)
# ---------------------------------------------------------------------------
_upstash_url: str | None = None
_upstash_token: str | None = None
_upstash_ready: bool | None = None


def _get_upstash_rest():
    """Return (url, token) for Upstash REST API, or (None, None) if not configured."""
    global _upstash_url, _upstash_token, _upstash_ready
    if _upstash_ready is not None:
        return _upstash_url, _upstash_token

    url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()

    if url and token:
        _upstash_url = url.rstrip("/")
        _upstash_token = token
        _upstash_ready = True
        logger.info("[cache] ✅ Upstash REST API configured: %s", _upstash_url)
    else:
        _upstash_ready = False
        logger.info("[cache] Upstash REST not configured — trying redis-py client.")

    return _upstash_url, _upstash_token


def _upstash_get(key: str) -> str | None:
    """GET key via Upstash REST API."""
    import urllib.request
    url, token = _get_upstash_rest()
    if not url:
        return None
    try:
        req = urllib.request.Request(
            f"{url}/get/{key}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("result")
    except Exception as exc:
        logger.warning("[cache] Upstash REST GET failed for %s: %s", key, exc)
        return None


def _upstash_setex(key: str, ttl: int, value: str) -> bool:
    """SETEX key via Upstash REST API."""
    import urllib.request
    url, token = _get_upstash_rest()
    if not url:
        return False
    try:
        body = json.dumps(["SET", key, value, "EX", ttl]).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True
    except Exception as exc:
        logger.warning("[cache] Upstash REST SET failed for %s: %s", key, exc)
        return False


# ---------------------------------------------------------------------------
# Standard redis-py client (singleton fallback)
# ---------------------------------------------------------------------------
_redis_client = None
_redis_checked = False


def _get_redis():
    """Return singleton redis-py client, or None if unavailable."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    _redis_checked = True
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return None

    try:
        import redis as redis_lib
        _redis_client = redis_lib.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            ssl_cert_reqs=ssl.CERT_NONE,
        )
        _redis_client.ping()
        logger.info("[cache] ✅ redis-py connected: %s", url.split("@")[-1])
    except Exception as exc:
        logger.warning("[cache] ⚠️ redis-py failed (%s) — using in-memory.", exc)
        _redis_client = None

    return _redis_client


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------
def _cache_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Cache decorator
# ---------------------------------------------------------------------------
def cache(ttl: int = 300, key_prefix: str = "api"):
    """
    Cache decorator for sync FastAPI route handlers.
    Priority: Upstash REST API → redis-py → in-memory.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ckey = _cache_key(key_prefix + ":" + func.__name__, *args, **kwargs)
            upstash_url, _ = _get_upstash_rest()

            # --- 1. Try Upstash REST ---
            if upstash_url:
                cached = _upstash_get(ckey)
                if cached:
                    try:
                        return json.loads(cached)
                    except Exception:
                        pass

            # --- 2. Try redis-py ---
            else:
                r = _get_redis()
                if r is not None:
                    try:
                        cached = r.get(ckey)
                        if cached:
                            return json.loads(cached)
                    except Exception as exc:
                        logger.warning("[cache] Redis GET failed for %s: %s", func.__name__, exc)

            # --- 3. Try in-memory ---
            if ckey in _memory_cache:
                val, exp = _memory_cache[ckey]
                if time.time() < exp:
                    return val
                del _memory_cache[ckey]

            # --- Execute function ---
            result = func(*args, **kwargs)

            serialized = json.dumps(
                result,
                default=lambda x: x.item() if hasattr(x, "item") else str(x),
            )

            # --- Store result ---
            if upstash_url:
                if not _upstash_setex(ckey, ttl, serialized):
                    _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))
            else:
                r = _get_redis()
                if r is not None:
                    try:
                        r.setex(ckey, ttl, serialized)
                    except Exception as exc:
                        logger.warning("[cache] Redis SET failed for %s: %s — memory fallback.", func.__name__, exc)
                        _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))
                else:
                    _memory_cache[ckey] = (result, time.time() + min(ttl, _MEMORY_TTL))

            return result

        return wrapper
    return decorator
