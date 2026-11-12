"""Server-Sent Events: one Broadcaster, every open screen subscribed to /api/events."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Awaitable, Callable


def format_sse(event_type: str, data: dict[str, Any]) -> str:
    return f'event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


class Broadcaster:
    def __init__(self, queue_size: int = 100) -> None:
        self._queue_size = queue_size
        self._subscribers: set[asyncio.Queue] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait((event_type, data))
            except asyncio.QueueFull:
                pass  # a stuck client loses events rather than blocking everyone; it resyncs on reconnect


async def sse_stream(broadcaster: Broadcaster, is_disconnected: Callable[[], Awaitable[bool]],
                     ping_every: float = 20.0) -> AsyncIterator[str]:
    q = broadcaster.subscribe()
    try:
        yield 'retry: 3000\n\n'
        while not await is_disconnected():
            try:
                event_type, data = await asyncio.wait_for(q.get(), timeout=ping_every)
            except asyncio.TimeoutError:
                if await is_disconnected():
                    break
                yield 'event: ping\ndata: {}\n\n'   # an EVENT, not a comment: the page's watchdog must see it
                continue
            yield format_sse(event_type, data)
    finally:
        broadcaster.unsubscribe(q)
