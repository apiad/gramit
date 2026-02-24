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

def test_extract_safe_chunk_with_partial_ansi():
    """
    Tests that partial ANSI sequences are kept in the buffer.
    """
    router = OutputRouter(MagicMock(), MagicMock())
    
    # Complete sequence
    router._buffer = "hello\x1b[31mworld"
    chunk = router._extract_safe_chunk()
    assert chunk == "hello\x1b[31mworld"
    assert router._buffer == ""
    
    # Partial sequence at end
    router._buffer = "hello\x1b["
    chunk = router._extract_safe_chunk()
    assert chunk == "hello"
    assert router._buffer == "\x1b["
    
    # Append more to complete it
    router._buffer += "31m"
    chunk = router._extract_safe_chunk()
    assert chunk == "\x1b[31m"
    assert router._buffer == ""

def test_extract_safe_chunk_with_esc_at_end():
    """
    Tests that an ESC character at the very end of the buffer is treated as partial.
    """
    router = OutputRouter(MagicMock(), MagicMock())
    router._buffer = "data\x1b"
    chunk = router._extract_safe_chunk()
    assert chunk == "data"
    assert router._buffer == "\x1b"

def test_extract_safe_chunk_long_partial_sequence():
    """
    Tests that very long (possibly invalid) sequences are eventually flushed
    to avoid infinite buffering.
    """
    router = OutputRouter(MagicMock(), MagicMock())
    # > 32 characters starting with \x1b
    long_garbage = "\x1b" + "a" * 40
    router._buffer = long_garbage
    chunk = router._extract_safe_chunk()
    # Heuristic in code is 32 chars
    assert chunk == long_garbage
    assert router._buffer == ""
