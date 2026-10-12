"""Fan-out of live job updates to connected dashboards.

Jobs run on worker threads while WebSocket clients live on the event loop,
so every publish hops threads explicitly. In-process today; the same
interface fits Redis pub/sub when workers move to their own machines.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

# Bounded so a stalled browser tab cannot grow a queue without limit.
SUBSCRIBER_QUEUE_SIZE = 256


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Record the loop that worker threads must publish through."""
        self._loop = loop

    @contextmanager
    def subscribe(self, topic: str) -> Iterator[asyncio.Queue]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        self._subscribers.setdefault(topic, set()).add(queue)
        try:
            yield queue
        finally:
            listeners = self._subscribers.get(topic)
            if listeners is not None:
                listeners.discard(queue)
                if not listeners:
                    del self._subscribers[topic]

    def publish_from_thread(self, topic: str, message: dict) -> None:
        """Publish from a worker thread. Safe to call with no subscribers."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._publish, topic, message)

    def _publish(self, topic: str, message: dict) -> None:
        for queue in self._subscribers.get(topic, set()):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # A client too slow to keep up loses updates rather than
                # stalling the counting worker behind it.
                pass


async def drain(queue: asyncio.Queue) -> AsyncIterator[dict]:
    while True:
        yield await queue.get()
