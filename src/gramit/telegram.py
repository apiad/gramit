from typing import List
from telegram import Update
from telegram.ext import ContextTypes

from .orchestrator import Orchestrator


class InputRouter:
    """
    Handles incoming Telegram messages and routes them to the orchestrator.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        authorized_chat_ids: List[int],
    ):
        self._orchestrator = orchestrator
        self._authorized_chat_ids = authorized_chat_ids
        print(f"InputRouter initialized. Authorized chat IDs: {authorized_chat_ids}")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the /start command."""
        if not update.message:
            return
        chat_id = update.message.chat.id
        print(f"InputRouter: Received /start command from chat ID {chat_id}.")
        await context.bot.send_message(chat_id=chat_id, text="Hello! I'm Gramit. Send me a command.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Primary message handler for the Telegram bot.
        """
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        text = update.message.text
        print(f"InputRouter: Received message from chat ID {chat_id}: '{text[:50]}...'")

        if chat_id not in self._authorized_chat_ids:
            print(f"InputRouter: Unauthorized chat ID {chat_id}. Ignoring message.")
            return

        print(f"InputRouter: Authorized message. (Orchestrator write temporarily disabled for debugging)")
        # await self._orchestrator.write(text + "\n") # Temporarily disabled
        # print("InputRouter: Message written to orchestrator.")

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handles incoming Telegram commands.
        """
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        command_text = update.message.text
        print(f"InputRouter: Received command from chat ID {chat_id}: '{command_text}'")

        if chat_id not in self._authorized_chat_ids:
            print(f"InputRouter: Unauthorized chat ID {chat_id}. Ignoring command.")
            return

        command = command_text.split(' ')[0] # Get the command part
        if command == "/quit":
            print("InputRouter: Handling /quit command.")
            await context.bot.send_message(
                chat_id=chat_id, text="Shutting down the orchestrated process."
            )
            await self._orchestrator.shutdown()
            print("InputRouter: Orchestrator shutdown initiated.")
