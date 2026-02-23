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
        command_text = update.message.text

        if chat_id not in self._authorized_chat_ids:
            return

        command = command_text.split(" ")[0]
        
        # 1. Check for standard /quit command
        if command == "/quit":
            await context.bot.send_message(
                chat_id=chat_id, text="Shutting down the orchestrated process."
            )
            await self._orchestrator.shutdown()
            self._shutdown_event.set()
            return

        # 2. Check for special key shortcuts
        key_sequence = self._parse_key_command(command)
        if key_sequence:
            await self._orchestrator.write(key_sequence)

    def _parse_key_command(self, cmd: str) -> Optional[str]:
        """
        Parses a command into a terminal key sequence.
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
        
        if cmd in mapping:
            return mapping[cmd]

        # Modifier combinations: /c<a>, /a<a>, /c/s<a>, etc.
        import re
        
        # Pattern to match modifiers and a final character
        # e.g., /c/sa -> groups ('/c/s', 'a')
        match = re.match(r"^((?:/[cas])+)((?:[a-zA-Z0-9])|enter|esc|t|b|d|up|down|left|right)$", cmd)
        if not match:
            return None
            
        modifiers, key = match.groups()
        
        # Resolve the base key first
        base_key = key
        if key in ["enter", "esc", "t", "b", "d", "up", "down", "left", "right"]:
            base_key = mapping["/" + key]
        
        result = base_key
        
        # Apply modifiers in reverse order (outermost last)
        # /c/sa -> apply Shift, then Control
        mod_list = modifiers.strip("/").split("/")
        
        for mod in reversed(mod_list):
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
                # For single characters, Shift just uppercases
                if len(result) == 1:
                    result = result.upper()
                # For other keys, Shift behavior varies by terminal,
                # but standard ANSI doesn't have a universal Shift+Enter that is different.
                # We'll just leave it as is for now.
                pass
                
        return result
