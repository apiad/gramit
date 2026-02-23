import asyncio
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from gramit.router import OutputRouter

@pytest.mark.asyncio
async def test_output_stream_no_pty_to_telegram():
    """
    Verifies that when output_stream is set, PTY data only goes to mirror,
    not to the Telegram sender.
    """
    orchestrator = MagicMock()
    orchestrator.is_alive.side_effect = [True, True, False]
    # PTY returns some "TUI-like" data
    orchestrator.read = AsyncMock(return_value=b"TUI CONTENT")
    
    sender = AsyncMock()
    
    router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        output_stream="fake.log",
        mirror=True
    )
    
    # Mock debouncer push to see what's sent to Telegram
    router._debouncer.push = AsyncMock()
    
    # Mock os.write to avoid fileno issues
    with patch("os.write"):
        # Run drain_pty for one iteration
        drain_task = asyncio.create_task(router._drain_pty())
        await asyncio.sleep(0.1)
        drain_task.cancel()
    
    # Assertions
    # The PTY data should NOT have pushed anything to the Telegram debouncer
    for call in router._debouncer.push.call_args_list:
        assert "TUI CONTENT" not in call.args[0]

@pytest.mark.asyncio
async def test_standard_mode_pty_to_telegram():
    """
    Verifies that in standard mode, PTY data goes to Telegram.
    """
    orchestrator = MagicMock()
    # Let it run then exit
    orchestrator.is_alive.side_effect = [True, False]
    orchestrator.read = AsyncMock(return_value=b"STANDARD CONTENT")
    
    sender = AsyncMock()
    
    router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        mirror=True
    )
    
    # Mock terminal methods to avoid fileno errors
    router._prepare_terminal = MagicMock()
    router._restore_terminal = MagicMock()
    
    # Mock debouncer push to see what's sent to Telegram
    router._debouncer.push = AsyncMock()
    
    with patch("os.write"):
        # We run the start method directly, it should finish when is_alive returns False
        await router.start()
    
    # Assertions
    # The PTY data SHOULD have been pushed to the Telegram debouncer
    # The final flush in start() pushes the remaining buffer
    found = False
    for call in router._debouncer.push.call_args_list:
        if "STANDARD CONTENT" in call.args[0]:
            found = True
            break
    assert found, "PTY data was not pushed to Telegram debouncer in standard mode"
