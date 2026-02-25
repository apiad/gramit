import asyncio
from typing import List, Callable, Any, Coroutine, TypeVar
from .utils import logger

T = TypeVar("T")


class AsyncDebouncer:
    """
    A debouncer that collects items and flushes them in a batch after a
    specified interval of inactivity or when the buffer reaches a maximum size.
    """

    def __init__(
        self,
        interval: float,
        flush_callback: Callable[[List[T]], Coroutine[Any, Any, None]],
        max_buffer_size: int = 100,
    ):
        """
        Initializes the AsyncDebouncer.

        Args:
            interval: The time in seconds to wait for inactivity before flushing.
            flush_callback: An async function to call with the batch of items.
            max_buffer_size: Maximum number of items to buffer before forcing a flush.
        """
        self._interval = interval
        self._flush_callback = flush_callback
        self._max_buffer_size = max_buffer_size
        self._buffer: List[T] = []
        self._task: asyncio.Task | None = None

    async def push(self, item: T):
        """
        Pushes an item into the debouncer buffer. 
        
        If the buffer reaches max_buffer_size, it flushes immediately.
        Otherwise, it resets the flush timer.

        Args:
            item: The item to add to the buffer.
        """
        self._buffer.append(item)

        if len(self._buffer) >= self._max_buffer_size:
            # Force immediate flush if buffer is full
            await self.flush()
        else:
            # Re-schedule the flush task (resetting the timer)
            if self._task:
                self._task.cancel()
            try:
                self._task = asyncio.create_task(self._wait_and_flush())
            except RuntimeError:
                # Event loop might be closing
                pass

    async def flush(self):
        """
        Immediately flushes the buffer, cancelling any pending flush task.
        """
        if self._task:
            self._task.cancel()
            self._task = None

        if self._buffer:
            items_to_flush = self._buffer[:]
            self._buffer.clear()
            try:
                await self._flush_callback(items_to_flush)
            except Exception as e:
                logger.error(f"AsyncDebouncer flush callback failed: {e}")

    async def _wait_and_flush(self):
        """
        Waits for the specified interval, then flushes the buffer if it hasn't 
        been cancelled.
        """
        try:
            await asyncio.sleep(self._interval)
            await self.flush()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"AsyncDebouncer wait_and_flush encountered an error: {e}")
        finally:
            self._task = None
