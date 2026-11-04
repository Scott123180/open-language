"""011 T029: iterate_in_thread, a sync token stream read from async code (research R13.2)."""

import asyncio
import threading

import pytest

from app.conversation_turns import iterate_in_thread

WAIT_SECONDS = 2


async def _collect(stream) -> list:
    return [item async for item in stream]


async def test_the_items_arrive_in_order():
    assert await _collect(iterate_in_thread(lambda: iter(["Hola", " a", " todos"]))) == [
        "Hola",
        " a",
        " todos",
    ]


async def test_the_iterator_runs_off_the_event_loops_thread():
    loop_thread = threading.get_ident()
    seen: list[int] = []

    def tokens():
        seen.append(threading.get_ident())
        yield "uno"

    await _collect(iterate_in_thread(tokens))

    assert seen and seen[0] != loop_thread


async def test_an_exception_from_the_iterator_is_raised_in_the_caller():
    def failing():
        yield "uno"
        raise ValueError("the model stopped")

    stream = iterate_in_thread(failing)

    assert await stream.__anext__() == "uno"
    with pytest.raises(ValueError, match="the model stopped"):
        await stream.__anext__()


async def test_closing_early_closes_the_sync_iterator_on_its_own_thread():
    loop_thread = threading.get_ident()
    closed_on: list[int] = []
    finished = threading.Event()

    def endless():
        try:
            while True:
                yield "otra"
        finally:
            closed_on.append(threading.get_ident())
            finished.set()

    stream = iterate_in_thread(endless)
    assert await stream.__anext__() == "otra"

    await stream.aclose()

    assert await asyncio.to_thread(finished.wait, WAIT_SECONDS)
    assert closed_on and closed_on[0] != loop_thread
