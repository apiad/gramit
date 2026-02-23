import asyncio
from typing import List, Callable, Any, Coroutine

T = Any


class AsyncDebouncer:
    """
    A debouncer that collects items and flushes them in a batch after a
    specified interval of inactivity.
    """

    def __init__(
        self,
        interval: float,
        flush_callback: Callable[[List[T]], Coroutine[Any, Any, None]],
    ):
        """
        Initializes the AsyncDebouncer.

        Args:
            interval: The time in seconds to wait for inactivity before flushing.
            flush_callback: An async function to call with the batch of items.
        """
        self._interval = interval
        self._flush_callback = flush_callback
        self._buffer: List[T] = []
        self._task: asyncio.Task | None = None

    async def push(self, item: T):
        """
        Pushes an item into the debouncer buffer and resets the flush timer.
        """
        # If there's a pending flush task, cancel it
        if self._task:
            self._task.cancel()

        self._buffer.append(item)
        # Schedule a new flush task
        self._task = asyncio.create_task(self._wait_and_flush())

    async def _wait_and_flush(self):
        """
        Waits for the specified interval, then flushes the buffer.
        """
        await asyncio.sleep(self._interval)
        items_to_flush = self._buffer[:]
        self._buffer.clear()
        await self._flush_callback(items_to_flush)
        self._task = None
