from typing import List, Optional
import asyncio
  # New import
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
        command_text = update.message.text.strip()

        if chat_id not in self._authorized_chat_ids:
            return

        # 1. Check for standard /quit command
        if command_text == "/quit":
            await context.bot.send_message(
                chat_id=chat_id, text="Shutting down the orchestrated process."
            )
            await self._orchestrator.shutdown()
            self._shutdown_event.set()
            return

        # 2. Check for special key shortcuts
        # We pass the full text now to handle space-separated modifiers
        key_sequence = self._parse_key_command(command_text)
        if key_sequence:
            await self._orchestrator.write(key_sequence)

    def _parse_key_command(self, text: str) -> Optional[str]:
        """
        Parses a command string into a terminal key sequence.
        Supports space-separated modifiers like "/c /s a".
        """
        # Simple Mappings
        mapping = {
            "/enter": "\r",
            "/esc": "\x1b",
            "/t": "\t",
            "/b": "\x7f",
            "/d": "\x1b[3~",
            "/up": "\x1b[A",
            "/down": "\x1b[B",
            "/left": "\x1b[D",
            "/right": "\x1b[C",
        }
        
        if text in mapping:
            return mapping[text]

        # Handle space-separated parts: "/c /s a"
        parts = text.split()
        if not parts:
            return None
            
        modifiers = []
        base_key_part = None
        
        for part in parts:
            if part in ["/c", "/a", "/s"]:
                modifiers.append(part[1:]) # keep 'c', 'a', or 's'
            elif part.startswith("/") and part in mapping:
                base_key_part = mapping[part]
            elif len(part) == 1:
                base_key_part = part
            elif part in ["enter", "esc", "t", "b", "d", "up", "down", "left", "right"]:
                base_key_part = mapping["/" + part]
            else:
                # Unknown part, bail out to avoid sending junk
                return None
                
        if base_key_part is None:
            return None
            
        result = base_key_part
        
        # Apply modifiers in reverse order (inner to outer)
        for mod in reversed(modifiers):
            if mod == "c": # Control
                if len(result) == 1:
                    c = result.lower()
                    if "a" <= c <= "z":
                        result = chr(ord(c) - ord("a") + 1)
                    elif c == "[": result = "\x1b"
                    elif c == "\\": result = "\x1c"
                    elif c == "]": result = "\x1d"
                    elif c == "^": result = "\x1e"
                    elif c == "_": result = "\x1f"
            elif mod == "a": # Alt/Meta
                result = "\x1b" + result
            elif mod == "s": # Shift
                if len(result) == 1:
                    result = result.upper()
                
        return result
