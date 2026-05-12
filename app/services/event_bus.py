from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_subscribers: defaultdict[str, list[asyncio.Queue]] = defaultdict(list)


def init(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def subscribe(key: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _subscribers[key].append(q)
    return q


def unsubscribe(key: str, q: asyncio.Queue) -> None:
    try:
        _subscribers[key].remove(q)
    except ValueError:
        pass


def publish(key: str, event: dict) -> None:
    if _loop is None:
        return
    for q in list(_subscribers.get(key, [])):
        _loop.call_soon_threadsafe(_safe_put, q, event)


def _safe_put(q: asyncio.Queue, event: dict) -> None:
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        pass  # slow consumer — drop new event
