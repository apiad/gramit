import asyncio
from unittest.mock import Mock, AsyncMock
import pytest

from gramit.debouncer import AsyncDebouncer


@pytest.mark.asyncio
async def test_debouncer_collects_and_flushes():
    """
    Tests that the debouncer collects multiple items and flushes them in a
    single batch after the interval has passed.
    """
    flush_callback = AsyncMock()
    debouncer = AsyncDebouncer(interval=0.1, flush_callback=flush_callback)

    # Push items rapidly
    await debouncer.push("item1")
    await debouncer.push("item2")
    await asyncio.sleep(0.05)
    await debouncer.push("item3")

    # At this point, the callback should not have been called
    flush_callback.assert_not_called()

    # Wait for the interval to elapse
    await asyncio.sleep(0.15)

    # Now the callback should have been called exactly once with all items
    flush_callback.assert_awaited_once_with(["item1", "item2", "item3"])
