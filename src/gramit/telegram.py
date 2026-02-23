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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Primary message handler for the Telegram bot.
        """
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id
        if chat_id not in self._authorized_chat_ids:
            # In a real app, maybe send a "not authorized" message
            return

        text = update.message.text
        # Assume input from Telegram is a command that needs a newline
        await self._orchestrator.write(text + "\n")
