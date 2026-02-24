import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from gramit.router import OutputRouter

@pytest.mark.asyncio
async def test_standard_mode_pty_to_telegram():
    """
    Verifies that in standard mode, PTY data goes to Telegram.
    """
    r_fd, w_fd = os.pipe()
    try:
        orchestrator = MagicMock()
        orchestrator._master_fd = r_fd
        # Let it run then exit
        orchestrator.is_alive.side_effect = [True, True, False]
        orchestrator.read = AsyncMock(return_value=b"STANDARD CONTENT")
    
        sender = AsyncMock()
    
        router = OutputRouter(
            orchestrator=orchestrator,
            sender=sender,
            mirror=False
        )
    
        # Mock terminal methods to avoid fileno errors
        router._prepare_terminal = MagicMock()
        router._restore_terminal = MagicMock()
    
        # Mock debouncer push to see what's sent to Telegram
        router._debouncer.push = AsyncMock()
    
        # Write data initially
        os.write(w_fd, b"STANDARD CONTENT\n")
            
        # Run start method in a task
        task = asyncio.create_task(router.start())
        
        # Give event loop time to process the pipe data
        await asyncio.sleep(0.1)
        
        # Wait for completion (since is_alive returns False eventually)
        await task
            
        # Data should have been pushed to debouncer
        router._debouncer.push.assert_awaited()
        # Check content of pushed data
        full_sent = "".join(call.args[0] for call in router._debouncer.push.await_args_list)
        assert "STANDARD CONTENT" in full_sent
    finally:
        os.close(r_fd)
        os.close(w_fd)

@pytest.mark.asyncio
async def test_output_stream_bypasses_pty_for_telegram():
    """
    Verifies that in output-stream mode, PTY data is NOT sent to Telegram,
    but the file content IS sent.
    """
    from gramit.router import FileTailer
    
    r_fd, w_fd = os.pipe()
    try:
        orchestrator = MagicMock()
        orchestrator._master_fd = r_fd
        orchestrator.is_alive.side_effect = [True, True, True, False]
    
        sender = AsyncMock()
    
        router = OutputRouter(
            orchestrator=orchestrator,
            sender=sender,
            mirror=False,
            output_stream="test_stream.log"
        )
    
        # Mock terminal methods
        router._prepare_terminal = MagicMock()
        router._restore_terminal = MagicMock()
    
        # Mock FileTailer to yield specific data
        with patch("gramit.router.FileTailer") as MockTailer:
            tailer_instance = MockTailer.return_value
            async def mock_read_new(orch):
                yield "FILE CONTENT"
                # Keep it alive for a bit
                await asyncio.sleep(0.05)
            tailer_instance.read_new = mock_read_new
    
            # Mock debouncer push
            router._debouncer.push = AsyncMock()
    
            # Start router
            task = asyncio.create_task(router.start())
            
            # Write data to PTY pipe - this SHOULD NOT go to Telegram
            os.write(w_fd, b"PTY CONTENT\n")
            
            await asyncio.sleep(0.1)
            await task
    
            # Assertions
            pushed_calls = [call.args[0] for call in router._debouncer.push.await_args_list]
            pushed_data = "".join(pushed_calls)
            
            # The file content should be pushed
            assert "FILE CONTENT" in pushed_data
            
            # The PTY content should NOT be in the pushed_data
            # IF THIS FAILS, THE BUG IS REPRODUCED
            assert "PTY CONTENT" not in pushed_data
    finally:
        os.close(r_fd)
        os.close(w_fd)
