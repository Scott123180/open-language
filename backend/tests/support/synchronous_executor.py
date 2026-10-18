"""An Executor that runs each task at once, on the caller's thread, so background work is
deterministic in tests."""

from concurrent.futures import Executor, Future


class SynchronousExecutor(Executor):
    def submit(self, fn, /, *args, **kwargs) -> Future:
        future: Future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as error:  # noqa: BLE001 — the future carries it, as a pool's would
            future.set_exception(error)
        return future
