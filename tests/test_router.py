import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from gramit.router import OutputRouter


@pytest.mark.asyncio
async def test_output_router_line_mode():
    """
    Tests that the OutputRouter in 'line' mode correctly buffers data,
    splits it by newlines, and sends complete lines to the sender.
    """
    # Mocks
    mock_orchestrator = MagicMock()
    mock_sender = AsyncMock()

    # Configure the mock orchestrator to simulate reading from stdout
    output_stream = ["hello ", "world\nthis is ", "a test\nand another line\n"]
    mock_orchestrator.read = AsyncMock(side_effect=output_stream)

    # Initialize the router
    router = OutputRouter(
        orchestrator=mock_orchestrator,
        sender=mock_sender,
        mode="line",
        debounce_interval=0.05,
    )

    # Start the router and let it run
    task = asyncio.create_task(router.start())
    await asyncio.sleep(0.1)  # Allow time for processing and debouncing

    # Stop the router
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass  # Expected

    # Assertions
    mock_sender.assert_awaited_once_with(
        "hello world\nthis is a test\nand another line"
    )


@pytest.mark.asyncio
async def test_output_router_handles_quick_exit():
    """
    Tests that the OutputRouter correctly flushes output from a process
    that exits immediately after writing.
    """
    mock_orchestrator = MagicMock()
    mock_sender = AsyncMock()

    # Simulate a process that writes "error" and immediately returns EOF
    mock_orchestrator.read = AsyncMock(side_effect=["error: command not found\n", ""])

    router = OutputRouter(
        orchestrator=mock_orchestrator,
        sender=mock_sender,
        mode="line",
        debounce_interval=0.1,
    )

    # The start method should now handle the entire lifecycle
    await router.start()

    # The final flush should have been called
    mock_sender.assert_awaited_once_with("error: command not found")
