from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import asyncio

from gramit.telegram import InputRouter


# Mocking the telegram bot Update and Message classes
class MockMessage:
    def __init__(self, text: str, chat_id: int):
        self.text = text
        self.chat = MagicMock()
        self.chat.id = chat_id


class MockUpdate:
    def __init__(self, text: str, chat_id: int):
        self.message = MockMessage(text, chat_id)


@pytest.mark.asyncio
async def test_input_router_handles_authorized_message():
    """
    Tests that the InputRouter correctly calls the orchestrator's write method
    for a message from an authorized chat ID.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,
    )

    update = MockUpdate(text="ls -l", chat_id=12345)
    
    # We patch asyncio.sleep to avoid waiting in tests
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await router.handle_message(update, context=None)
        
        # Expect two separate calls now: text, then \r after sleep
        assert mock_orchestrator.write.call_count == 2
        mock_orchestrator.write.assert_any_call("ls -l")
        mock_orchestrator.write.assert_any_call("\r")
        mock_sleep.assert_awaited_once_with(0.2)
    
    mock_shutdown_event.set.assert_not_called()


@pytest.mark.asyncio
async def test_input_router_quit_command():
    """
    Tests that the InputRouter correctly handles the /quit command,
    shutting down the orchestrator and sending a confirmation.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.shutdown = AsyncMock()

    mock_context = MagicMock()
    mock_context.bot.send_message = AsyncMock()
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,
    )

    # Test /quit
    update = MockUpdate(text="/quit", chat_id=12345)
    await router.handle_command(update, mock_context)
    mock_orchestrator.shutdown.assert_awaited()
    mock_context.bot.send_message.assert_awaited_with(
        chat_id=12345,
        text="Shutting down the orchestrated process.",
        parse_mode="Markdown",
    )
    mock_shutdown_event.set.assert_called_once()
    
    # Reset mocks for next test
    mock_context.bot.send_message.reset_mock()

    # Test /help
    update = MockUpdate(text="/help", chat_id=12345)
    await router.handle_command(update, mock_context)
    # Just check if send_message was called with some help text
    mock_context.bot.send_message.assert_awaited_once()
    args, kwargs = mock_context.bot.send_message.call_args
    assert "Gramit Help" in kwargs["text"]
    assert "Key Shortcuts" in kwargs["text"]


@pytest.mark.asyncio
async def test_input_router_key_shortcuts():
    """
    Tests that the InputRouter correctly parses and sends key shortcuts.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,
    )

    # Test /enter
    await router.handle_command(MockUpdate(text="/enter", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\r")

    # Test /c a (Ctrl+A)
    await router.handle_command(MockUpdate(text="/c a", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x01")

    # Test /c /s a (Ctrl+Shift+A)
    await router.handle_command(MockUpdate(text="/c /s a", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x01")

    # Test /a x (Alt+x)
    await router.handle_command(MockUpdate(text="/a x", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x1bx")

    # Test /up
    await router.handle_command(MockUpdate(text="/up", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x1b[A")
    
    # Test /home
    await router.handle_command(MockUpdate(text="/home", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x1b[H")

    # Test /end
    await router.handle_command(MockUpdate(text="/end", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x1b[F")

    # Test /f1
    await router.handle_command(MockUpdate(text="/f1", chat_id=12345), None)
    mock_orchestrator.write.assert_awaited_with("\x1bOP")


@pytest.mark.asyncio
async def test_input_router_multiline_message():
    """
    Tests that multi-line messages are handled correctly with inject_enter.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()
    mock_shutdown_event = MagicMock(spec=asyncio.Event)

    # Test with inject_enter=True (default)
    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,
        inject_enter=True,
    )
    
    update = MockUpdate(text="line1\nline2", chat_id=12345)
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await router.handle_message(update, context=None)
        assert mock_orchestrator.write.call_count == 2
        mock_orchestrator.write.assert_any_call("line1\nline2")
        mock_orchestrator.write.assert_any_call("\r")
        mock_sleep.assert_awaited_once_with(0.2)
    
    mock_orchestrator.write.reset_mock()
    
    # Test with inject_enter=False
    router._inject_enter = False
    await router.handle_message(update, context=None)
    mock_orchestrator.write.assert_awaited_once_with("line1\nline2")


@pytest.mark.asyncio
async def test_input_router_ignores_unauthorized_message():
    """
    Tests that the InputRouter ignores messages from unauthorized chat IDs.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,
    )

    # Message from a different user
    update = MockUpdate(text="some command", chat_id=99999)
    await router.handle_message(update, context=None)

    mock_orchestrator.write.assert_not_awaited()
    mock_shutdown_event.set.assert_not_called()
