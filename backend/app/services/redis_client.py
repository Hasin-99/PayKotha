from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.core.config import get_settings

_memory: dict[str, Any] = {}
_redis = None


def _client():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis

        settings = get_settings()
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis = client
        return _redis
    except Exception:
        _redis = False
        return None


def set_json(key: str, value: dict, ttl: int = 60) -> None:
    client = _client()
    raw = json.dumps(value)
    if client:
        client.setex(key, ttl, raw)
    else:
        _memory[key] = raw


def get_json(key: str) -> Optional[dict]:
    client = _client()
    if client:
        raw = client.get(key)
    else:
        raw = _memory.get(key)
    if not raw:
        return None
    return json.loads(raw)


def incr(key: str, ttl: int = 60) -> int:
    client = _client()
    if client:
        val = client.incr(key)
        if val == 1:
            client.expire(key, ttl)
        return int(val)
    _memory[key] = str(int(_memory.get(key, "0")) + 1)
    return int(_memory[key])
