from typing import List
import asyncio  # New import
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
        shutdown_event: asyncio.Event,  # New parameter
    ):
        self._orchestrator = orchestrator
        self._authorized_chat_ids = authorized_chat_ids
        self._shutdown_event = shutdown_event  # Store the event

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Primary message handler for the Telegram bot.
        """
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        text = update.message.text

        if chat_id not in self._authorized_chat_ids:
            return

        # Many TUIs and interactive shells expect \r for Enter
        await self._orchestrator.write(text + "\r")

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handles incoming Telegram commands.
        """
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        command_text = update.message.text

        if chat_id not in self._authorized_chat_ids:
            return

        command = command_text.split(" ")[0]  # Get the command part
        if command == "/quit":
            await context.bot.send_message(
                chat_id=chat_id, text="Shutting down the orchestrated process."
            )
            await self._orchestrator.shutdown()
            self._shutdown_event.set()  # New: Signal shutdown
