from unittest.mock import AsyncMock, MagicMock
import pytest
import asyncio # New import

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
    mock_shutdown_event = AsyncMock(spec=asyncio.Event) # New mock

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event # Pass the mock event
    )

    update = MockUpdate(text="ls -l", chat_id=12345)
    await router.handle_message(update, context=None)

    # Expect the text to be written to the orchestrator with a newline
    mock_orchestrator.write.assert_awaited_once_with("ls -l\n")
    mock_shutdown_event.set.assert_not_called() # Should not be called


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
    mock_shutdown_event = AsyncMock(spec=asyncio.Event) # New mock

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],
        shutdown_event=mock_shutdown_event # Pass the mock event
    )

    update = MockUpdate(text="/quit", chat_id=12345)
    await router.handle_command(update, mock_context)

    mock_orchestrator.shutdown.assert_awaited_once()
    mock_context.bot.send_message.assert_awaited_once_with(
        chat_id=12345, text="Shutting down the orchestrated process."
    )
    mock_shutdown_event.set.assert_called_once() # Assert set was called


@pytest.mark.asyncio
async def test_input_router_ignores_unauthorized_message():
    """
    Tests that the InputRouter ignores messages from unauthorized chat IDs.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()
    mock_shutdown_event = AsyncMock(spec=asyncio.Event) # New mock

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345],  # Authorized user
        shutdown_event=mock_shutdown_event # Pass the mock event
    )

    # Message from a different user
    update = MockUpdate(text="some command", chat_id=99999)
    await router.handle_message(update, context=None)

    mock_orchestrator.write.assert_not_awaited()
    mock_shutdown_event.set.assert_not_called() # Should not be called

