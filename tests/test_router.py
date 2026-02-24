import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from gramit.router import OutputRouter

@pytest.mark.asyncio
async def test_output_router_line_mode():
    """
    Tests that the OutputRouter correctly handles PTY data via the new
    reader-based architecture.
    """
    # Create a real pipe for PTY emulation
    r_fd, w_fd = os.pipe()
    
    try:
        mock_orchestrator = MagicMock()
        mock_orchestrator._master_fd = r_fd
        # Simulate being alive until we write our data
        mock_orchestrator.is_alive.side_effect = [True, True, False]
        
        mock_sender = AsyncMock()
    
        router = OutputRouter(
            orchestrator=mock_orchestrator,
            sender=mock_sender,
            mode="line",
            debounce_interval=0.01,
            mirror=False # Avoid stdout issues in tests
        )
    
        # Start router
        task = asyncio.create_task(router.start())
        
        # Write to the pipe
        os.write(w_fd, b"hello world\nthis is a test\n")
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Stop router by making is_alive return False
        await task
    
        # Assertions
        mock_sender.assert_awaited()
        # The exact call depends on debouncing, but it should contain the text
        full_sent = "".join(call.args[0] for call in mock_sender.await_args_list)
        assert "hello world" in full_sent
        assert "this is a test" in full_sent
    finally:
        os.close(r_fd)
        os.close(w_fd)

@pytest.mark.asyncio
async def test_output_router_handles_quick_exit():
    """
    Tests that the OutputRouter correctly flushes output from a process
    that exits immediately after writing.
    """
    r_fd, w_fd = os.pipe()
    try:
        mock_orchestrator = MagicMock()
        mock_orchestrator._master_fd = r_fd
        mock_orchestrator.is_alive.side_effect = [True, False]
        
        mock_sender = AsyncMock()
    
        router = OutputRouter(
            orchestrator=mock_orchestrator,
            sender=mock_sender,
            mode="line",
            debounce_interval=0.1,
            mirror=False
        )
    
        # Write data then "exit"
        os.write(w_fd, b"error: command not found\n")
        
        # The start method handles lifecycle
        await router.start()
    
        # The final flush should have been called
        mock_sender.assert_awaited()
        full_sent = "".join(call.args[0] for call in mock_sender.await_args_list)
        assert "error: command not found" in full_sent
    finally:
        os.close(r_fd)
        os.close(w_fd)

@pytest.mark.asyncio
async def test_terminal_cleanup_once():
    """
    Verifies that restore_terminal only performs restoration once.
    """
    mock_orchestrator = MagicMock()
    router = OutputRouter(
        orchestrator=mock_orchestrator,
        sender=AsyncMock(),
        mirror=True
    )
    
    # Mocking necessary parts for terminal handling
    with patch("termios.tcgetattr"), \
         patch("termios.tcsetattr"), \
         patch("tty.setraw"), \
         patch("os.write") as mock_write:
        
        router.prepare_terminal()
        router.restore_terminal()
        
        # Capture how many times restoration sequences were written
        first_call_count = mock_write.call_count
        
        router.restore_terminal()
        # Should NOT have increased
        assert mock_write.call_count == first_call_count
