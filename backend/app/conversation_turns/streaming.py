"""Reading a blocking token stream from async code, item by item (011 research R13.2).

The conversation engine's sessions are synchronous: they block on the model. A line that is
spoken sentence by sentence needs each token as it comes, so the stream runs on a worker thread
and hands each item to the event loop. Closing the async side closes the sync iterator on its
own thread, so a session's clean-up never runs on the event loop.
"""

import asyncio
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Failure:
    error: BaseException


_END = object()


async def iterate_in_thread(make_iterator: Callable[[], Iterator]) -> AsyncIterator:
    """Run `make_iterator()` in the default executor and yield its items as they arrive."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    stop = threading.Event()
    loop.run_in_executor(None, _pump, make_iterator, _Handover(loop, queue), stop)
    try:
        while (item := await queue.get()) is not _END:
            if isinstance(item, _Failure):
                raise item.error
            yield item
    finally:
        stop.set()


@dataclass(frozen=True, slots=True)
class _Handover:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue

    def put(self, item) -> None:
        """Hand an item to the loop, unless the loop has already gone."""
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.queue.put_nowait, item)


def _pump(make_iterator: Callable[[], Iterator], handover: _Handover, stop: threading.Event):
    """On the worker thread: pass on every item, then the end or the failure."""
    iterator = None
    try:
        iterator = make_iterator()
        for item in iterator:
            if stop.is_set():
                break
            handover.put(item)
    except Exception as exc:  # noqa: BLE001 — every failure is raised again in the caller
        handover.put(_Failure(exc))
        return
    finally:
        _close(iterator)
    handover.put(_END)


def _close(iterator) -> None:
    close = getattr(iterator, "close", None)
    if close is not None:
        close()
