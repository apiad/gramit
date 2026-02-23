import asyncio
from typing import Callable, Coroutine, Any

from .orchestrator import Orchestrator
from .debouncer import AsyncDebouncer


class OutputRouter:
    """
    Reads output from the orchestrator, processes it based on the mode,
    and sends it to the specified sender.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        sender: Callable[[str], Coroutine[Any, Any, None]],
        mode: str = "line",
        debounce_interval: float = 0.5,
    ):
        self._orchestrator = orchestrator
        self._sender = sender
        self._mode = mode
        self._buffer = ""
        self._debouncer = AsyncDebouncer(debounce_interval, self._flush_buffer)

    async def start(self):
        """
        Starts the main loop to read and route output.
        """
        while True:
            try:
                data = await self._orchestrator.read(1024)
                if not data:
                    # EOF
                    break

                if self._mode == "line":
                    await self._process_line_mode(data)

            except asyncio.CancelledError:
                break
            except Exception:
                # In a real app, log this error
                break

        # Before final flush, push any remaining data in the internal buffer
        if self._buffer:
            await self._debouncer.push(self._buffer)
            self._buffer = ""  # Clear it after pushing

        # Now, force a final flush for any remaining buffered items in the debouncer
        await self._debouncer.flush()

    async def _process_line_mode(self, data: str):
        self._buffer += data

        # Split by newline, keeping the last (potentially incomplete) part
        lines = self._buffer.split("\n")
        self._buffer = lines.pop()  # Store the last part back in buffer

        for line in lines:
            if line:  # Only push non-empty lines
                await self._debouncer.push(line)

    async def _flush_buffer(self, items: list[str]):
        if not items:
            return

        full_message = "\n".join(items)
        await self._sender(full_message)
