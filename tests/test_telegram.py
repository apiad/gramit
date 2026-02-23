from unittest.mock import AsyncMock, MagicMock
import pytest

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

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345]
    )

    update = MockUpdate(text="ls -l", chat_id=12345)
    await router.handle_message(update, context=None)

    # Expect the text to be written to the orchestrator with a newline
    mock_orchestrator.write.assert_awaited_once_with("ls -l\n")


@pytest.mark.asyncio
async def test_input_router_ignores_unauthorized_message():
    """
    Tests that the InputRouter ignores messages from unauthorized chat IDs.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.write = AsyncMock()

    router = InputRouter(
        orchestrator=mock_orchestrator,
        authorized_chat_ids=[12345]  # Authorized user
    )

    # Message from a different user
    update = MockUpdate(text="some command", chat_id=99999)
    await router.handle_message(update, context=None)

    mock_orchestrator.write.assert_not_awaited()

