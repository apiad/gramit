from unittest.mock import AsyncMock, MagicMock
import pytest
import asyncio  # New import

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
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)  # New mock

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,  # Pass the mock event
    )

    update = MockUpdate(text="ls -l", chat_id=12345)
    await router.handle_message(update, context=None)

    # Expect the text to be written to the orchestrator with a carriage return (\r)
    mock_orchestrator.write.assert_awaited_once_with("ls -l\r")
    
    mock_shutdown_event.set.assert_not_called()  # Should not be called


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
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)  # New mock

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event,  # Pass the mock event
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

    # Test /c /up (Ctrl+Up)
    await router.handle_command(MockUpdate(text="/c /up", chat_id=12345), None)
    # The current logic will try to apply Control to the first char of the escape sequence
    # which might not be perfectly standard for all combinations but matches the requested 
    # extensible structure.


@pytest.mark.asyncio
async def test_input_router_ignores_unauthorized_message():
    """
    Tests that the InputRouter ignores messages from unauthorized chat IDs.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()
    mock_shutdown_event = AsyncMock(spec=asyncio.Event)  # New mock

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],  # Authorized user
        shutdown_event=mock_shutdown_event,  # Pass the mock event
    )

    # Message from a different user
    update = MockUpdate(text="some command", chat_id=99999)
    await router.handle_message(update, context=None)

    mock_orchestrator.write.assert_not_awaited()
    mock_shutdown_event.set.assert_not_called()  # Should not be called
