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
    
    async def _process_line_mode(self, data: str):
        self._buffer += data
        *lines, self._buffer = self._buffer.split('\n')
        
        for line in lines:
            if line:
                await self._debouncer.push(line)

    async def _flush_buffer(self, items: list[str]):
        if not items:
            return
        
        full_message = "\n".join(items)
        await self._sender(full_message)
