from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

# In-process fanout for live wallet updates (Redis optional later)
_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


def publish(user_id: str, event: dict[str, Any]) -> None:
    dead: list[asyncio.Queue] = []
    for q in _queues.get(user_id, []):
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        if q in _queues[user_id]:
            _queues[user_id].remove(q)


def subscribe(user_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=32)
    _queues[user_id].append(q)
    return q


def unsubscribe(user_id: str, q: asyncio.Queue) -> None:
    if q in _queues.get(user_id, []):
        _queues[user_id].remove(q)
