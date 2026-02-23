from typing import List
import asyncio # New import
from telegram import Update
from telegram.ext import ContextTypes

from .orchestrator import Orchestrator
from .router import OutputRouter


class InputRouter:
    """
    Handles incoming Telegram messages and routes them to the orchestrator.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        authorized_chat_ids: List[int],
        shutdown_event: asyncio.Event, # New parameter
    ):
        self._orchestrator = orchestrator
        self._authorized_chat_ids = authorized_chat_ids
        self._shutdown_event = shutdown_event # Store the event
        print(f"InputRouter initialized. Authorized chat IDs: {authorized_chat_ids}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Primary message handler for the Telegram bot.
        """
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        text = update.message.text
        print(f"InputRouter: Received message from chat ID {chat_id}: '{text[:50]}...')")

        if chat_id not in self._authorized_chat_ids:
            print(f"InputRouter: Unauthorized chat ID {chat_id}. Ignoring message.")
            return

        print(f"InputRouter: Authorized message. Writing to orchestrator.")
        await self._orchestrator.write(text + "\n")
        print("InputRouter: Message written to orchestrator.")

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
            self._shutdown_event.set() # New: Signal shutdown
            print("InputRouter: Orchestrator shutdown initiated and shutdown event set.")
