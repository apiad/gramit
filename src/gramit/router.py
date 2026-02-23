import asyncio
import os
from typing import Callable, Coroutine, Any, Optional

from .orchestrator import Orchestrator
from .debouncer import AsyncDebouncer


class FileTailer:
    """
    Asynchronously tails a file for new content.
    """

    def __init__(self, file_path: str, poll_interval: float = 0.1):
        self._file_path = file_path
        self._poll_interval = poll_interval
        self._stop_event = asyncio.Event()

    async def read_new(self):
        """
        A generator that yields new content appended to the file.
        Wait for the file to be created if it doesn't exist yet.
        """
        # Wait for file to exist
        while not os.path.exists(self._file_path):
            if self._stop_event.is_set():
                return
            await asyncio.sleep(self._poll_interval)

        with open(self._file_path, "r", encoding="utf-8", errors="replace") as f:
            # If the file exists but we are just starting, we might want to 
            # decide whether to start from the beginning or the end.
            # For now, let's start from the current end to truly "tail"
            # UNLESS it's the very first time we see content in it.
            f.seek(0, os.SEEK_END)
            last_pos = f.tell()

            while not self._stop_event.is_set():
                # Check if file shrunk (truncated)
                current_size = os.path.getsize(self._file_path)
                if current_size < last_pos:
                    f.seek(0)
                
                line = f.readline()
                if not line:
                    await asyncio.sleep(self._poll_interval)
                    last_pos = f.tell()
                    continue
                
                yield line
                last_pos = f.tell()

    def stop(self):
        self._stop_event.set()


class OutputRouter:
    """
    Reads output from the orchestrator OR a file stream, processes it,
    and sends it to the specified sender.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        sender: Callable[[str], Coroutine[Any, Any, None]],
        mode: str = "line",
        debounce_interval: float = 0.5,
        max_buffer_lines: int = 50,
        output_stream: Optional[str] = None,
    ):
        self._orchestrator = orchestrator
        self._sender = sender
        self._mode = mode
        self._buffer = ""
        self._debouncer = AsyncDebouncer(
            debounce_interval, self._flush_buffer, max_buffer_size=max_buffer_lines
        )
        self._output_stream = output_stream
        self._tailer: Optional[FileTailer] = None

    async def start(self):
        """
        Starts the main loop to read and route output.
        """
        if self._output_stream:
            self._tailer = FileTailer(self._output_stream)
            async for data in self._tailer.read_new():
                await self._process_line_mode(data)
        else:
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

        # Cleanup and final flushes
        if self._tailer:
            self._tailer.stop()

        # Before final flush, push any remaining data in the internal buffer
        if self._buffer:
            await self._debouncer.push(self._buffer)
            self._buffer = ""

        # Now, force a final flush
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

        # Telegram message limit is 4096 characters
        MAX_TELEGRAM_MSG = 4096
        if len(full_message) > MAX_TELEGRAM_MSG:
            # Trim the message if it's too long
            half_limit = (MAX_TELEGRAM_MSG // 2) - 50
            full_message = (
                full_message[:half_limit]
                + "\n\n... [Output trimmed due to size] ...\n\n"
                + full_message[-half_limit:]
            )

        await self._sender(full_message)
