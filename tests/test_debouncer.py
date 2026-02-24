import asyncio
from unittest.mock import AsyncMock
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


@pytest.mark.asyncio
async def test_debouncer_flushes_when_buffer_full():
    """
    Tests that the debouncer flushes immediately when the max_buffer_size is reached.
    """
    flush_callback = AsyncMock()
    debouncer = AsyncDebouncer(
        interval=1.0, flush_callback=flush_callback, max_buffer_size=3
    )

    # Push items up to the limit
    await debouncer.push("item1")
    await debouncer.push("item2")
    flush_callback.assert_not_called()

    # The 3rd item should trigger an immediate flush
    await debouncer.push("item3")

    # Callback should have been called immediately without waiting for interval
    flush_callback.assert_awaited_once_with(["item1", "item2", "item3"])

@pytest.mark.asyncio
async def test_debouncer_multiple_flushes():
    """
    Tests multiple consecutive flushes under pressure.
    """
    mock_callback = AsyncMock()
    debouncer = AsyncDebouncer(interval=0.01, flush_callback=mock_callback, max_buffer_size=2)
    
    # First batch (via size)
    await debouncer.push("1")
    await debouncer.push("2")
    assert mock_callback.call_count == 1
    
    # Second batch (via size)
    await debouncer.push("3")
    await debouncer.push("4")
    assert mock_callback.call_count == 2
    
    # Third batch (via timeout)
    await debouncer.push("5")
    await asyncio.sleep(0.05)
    assert mock_callback.call_count == 3
    
    mock_callback.assert_any_call(["1", "2"])
    mock_callback.assert_any_call(["3", "4"])
    mock_callback.assert_any_call(["5"])
