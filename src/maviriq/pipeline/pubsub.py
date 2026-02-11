"""In-memory pub/sub for pipeline SSE events.

Each run_id gets a list of subscriber queues. The pipeline runner
publishes events, and each connected SSE client receives them
instantly via its own asyncio.Queue — no DB polling needed.
"""

import asyncio
from collections import defaultdict

from maviriq.pipeline.events import SSEEvent

_subscribers: dict[str, list[asyncio.Queue[SSEEvent | None]]] = defaultdict(list)


def subscribe(run_id: str) -> asyncio.Queue[SSEEvent | None]:
    """Create a new subscription queue for a run. Returns the queue."""
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
    _subscribers[run_id].append(queue)
    return queue


def unsubscribe(run_id: str, queue: asyncio.Queue[SSEEvent | None]) -> None:
    """Remove a subscription queue. Cleans up if no subscribers left."""
    subs = _subscribers.get(run_id)
    if subs:
        try:
            subs.remove(queue)
        except ValueError:
            pass
        if not subs:
            del _subscribers[run_id]


def publish(run_id: str, event: SSEEvent | None) -> None:
    """Push an event to all subscribers for a run.

    Send None to signal the stream is done (completed/failed).
    """
    for queue in _subscribers.get(run_id, []):
        queue.put_nowait(event)
