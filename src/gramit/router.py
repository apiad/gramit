import asyncio
import io
import os
import re
from typing import Callable, Coroutine, Any, Optional

from .orchestrator import Orchestrator
from .debouncer import AsyncDebouncer
from .terminal import TerminalManager
from .utils import (
    logger,
)

# Regex for matching ANSI escape sequences (CSI, OSC, etc.)
# This is a broad regex to capture most common sequences
ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class FileTailer:
    """
    Asynchronously tails a file for new content.
    """

    def __init__(self, file_path: str, poll_interval: float = 0.1):
        """
        Initializes the FileTailer.

        Args:
            file_path: Path to the file to tail.
            poll_interval: Interval in seconds to poll for new data.
        """
        self._file_path = file_path
        self._poll_interval = poll_interval
        self._stop_event = asyncio.Event()

    async def read_new(self, orchestrator: Orchestrator):
        """
        A generator that yields new content appended to the file.
        Wait for the file to be created if it doesn't exist yet.

        Args:
            orchestrator: The orchestrator whose process lifecycle we follow.
        """
        # Wait for file to exist OR process to die
        while not os.path.exists(self._file_path):
            if self._stop_event.is_set() or not orchestrator.is_alive():
                return
            await asyncio.sleep(self._poll_interval)

        loop = asyncio.get_running_loop()
        
        # We'll reopen the file if it's replaced/rotated
        while not self._stop_event.is_set() and orchestrator.is_alive():
            try:
                with open(self._file_path, "r", encoding="utf-8", errors="replace") as f:
                    # Seek to end initially
                    f.seek(0, os.SEEK_END)
                    last_pos = f.tell()
                    inode = os.fstat(f.fileno()).st_ino

                    while not self._stop_event.is_set() and orchestrator.is_alive():
                        # Check if file was rotated or replaced
                        try:
                            curr_stat = os.stat(self._file_path)
                            if curr_stat.st_ino != inode:
                                break # Reopen file
                            
                            # Check for truncation
                            if curr_stat.st_size < last_pos:
                                f.seek(0)
                                last_pos = 0
                        except FileNotFoundError:
                            break # File moved/deleted, wait for it to reappear

                        # Read available data
                        data = await loop.run_in_executor(None, f.read, 4096)
                        
                        if not data:
                            await asyncio.sleep(self._poll_interval)
                            continue
                        
                        yield data
                        last_pos = f.tell()
            except Exception as e:
                logger.debug(f"FileTailer encountered an error reading {self._file_path}: {e}")
                await asyncio.sleep(self._poll_interval)
                continue

    def stop(self):
        """Stops the file tailing process."""
        self._stop_event.set()


class OutputRouter:
    """
    Reads output from the orchestrator OR a file stream, processes it,
    and sends it to the specified sender (Telegram).
    
    It also handles local terminal mirroring and input routing.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        sender: Callable[[str], Coroutine[Any, Any, None]],
        mode: str = "line",
        debounce_interval: float = 0.5,
        max_buffer_lines: int = 50,
        output_stream: Optional[str] = None,
        mirror: bool = True,
    ):
        """
        Initializes the OutputRouter.

        Args:
            orchestrator: The PTY orchestrator.
            sender: Async function to send messages to Telegram.
            mode: Routing mode (currently "line").
            debounce_interval: Time to wait before flushing to Telegram.
            max_buffer_lines: Max lines to buffer before forced Telegram flush.
            output_stream: Path to a file to tail instead of PTY stdout.
            mirror: Whether to mirror output to the local terminal.
        """
        self._orchestrator = orchestrator
        self._sender = sender
        self._mode = mode
        self._buffer = ""
        self._mirror_buffer = b""
        self._debouncer = AsyncDebouncer(
            debounce_interval, self._flush_buffer, max_buffer_size=max_buffer_lines
        )
        self._output_stream = output_stream
        self._mirror = mirror
        self._tailer: Optional[FileTailer] = None
        self._terminal_manager = TerminalManager(enabled=mirror)
        self._mirror_timer: Optional[asyncio.TimerHandle] = None
        self._mirror_debounce_interval = 0.04 # 40ms for better TUI quiescence (approx 25fps)

    async def start(self):
        """
        Starts the main loop to read and route output.
        """
        self._setup_readers()

        try:
            if self._output_stream:
                self._tailer = FileTailer(self._output_stream)
                async for data in self._tailer.read_new(self._orchestrator):
                    await self._handle_new_data(data, telegram_only=True)
            else:
                # In standard mode, the readers (callbacks) do the work.
                # We just wait for the process to exit.
                while self._orchestrator.is_alive():
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup_readers()
            await self._final_flush()

    def _setup_readers(self):
        """
        Configures asynchronous loop readers for the PTY master and local stdin.
        """
        loop = asyncio.get_running_loop()
        master_fd = self._orchestrator._master_fd
        if master_fd is not None:
            loop.add_reader(master_fd, self._on_pty_readable)

        if self._mirror:
            import sys
            try:
                stdin_fd = sys.stdin.fileno()
                loop.add_reader(stdin_fd, self._on_stdin_readable)
            except (Exception, io.UnsupportedOperation) as e:
                logger.debug(f"Could not add reader for stdin: {e}")

    def _cleanup_readers(self):
        """
        Removes previously registered asynchronous loop readers.
        """
        loop = asyncio.get_running_loop()
        master_fd = self._orchestrator._master_fd
        if master_fd is not None:
            loop.remove_reader(master_fd)
        
        import sys
        try:
            loop.remove_reader(sys.stdin.fileno())
        except Exception:
            pass
            
        if self._tailer:
            self._tailer.stop()

    async def _final_flush(self):
        """
        Performs a final flush of all remaining data in both mirror and Telegram buffers.
        """
        if self._buffer:
            await self._debouncer.push(self._buffer)
            self._buffer = ""
        if self._mirror_buffer:
            self._flush_mirror()
        await self._debouncer.flush()

    def _on_pty_readable(self):
        """
        Callback executed when the PTY master file descriptor is ready for reading.
        Reads data and routes it to the appropriate destinations.
        """
        try:
            data = os.read(self._orchestrator._master_fd, 4096)
            if not data:
                return
            
            # If output_stream is set, PTY data should be mirror-only
            asyncio.create_task(self._handle_new_data(data, mirror_only=bool(self._output_stream)))
        except Exception as e:
            logger.debug(f"Error reading from PTY: {e}")

    def _on_stdin_readable(self):
        """
        Callback executed when the local stdin file descriptor is ready for reading.
        Reads input and writes it to the PTY orchestrated process.
        """
        import sys
        try:
            data = os.read(sys.stdin.fileno(), 4096)
            if data:
                asyncio.create_task(self._orchestrator.write(data))
        except Exception as e:
            logger.debug(f"Error reading from stdin: {e}")

    async def _handle_new_data(self, data: str | bytes, mirror_only: bool = False, telegram_only: bool = False):
        """
        Routes incoming data to the local terminal mirror and/or the Telegram debouncer.

        Args:
            data: The incoming string or byte data.
            mirror_only: If True, only routes to the local terminal.
            telegram_only: If True, only routes to the Telegram debouncer.
        """
        if self._mirror and not telegram_only:
            self._route_to_mirror(data)
            
        if not mirror_only:
            await self._route_to_telegram(data)

    def _route_to_mirror(self, data: str | bytes):
        """
        Appends data to the mirror buffer and schedules an asynchronous flush.

        Args:
            data: The data to mirror locally.
        """
        if isinstance(data, str):
            self._mirror_buffer += data.encode('utf-8', errors='replace')
        else:
            self._mirror_buffer += data
        self._schedule_mirror_flush()

    async def _route_to_telegram(self, data: str | bytes):
        """
        Appends data to the Telegram buffer and pushes complete ANSI-safe chunks to the debouncer.

        Args:
            data: The data to route to Telegram.
        """
        if isinstance(data, bytes):
            text = data.decode('utf-8', errors='replace')
        else:
            text = data

        self._buffer += text
        safe_chunk = self._extract_safe_chunk()
        if safe_chunk:
            await self._debouncer.push(safe_chunk)

    def _schedule_mirror_flush(self):
        """Schedules a flush to the local terminal with debouncing."""
        if self._mirror_timer:
            self._mirror_timer.cancel()
        
        try:
            loop = asyncio.get_running_loop()
            self._mirror_timer = loop.call_later(
                self._mirror_debounce_interval, self._flush_mirror
            )
        except RuntimeError:
            # Loop might be closing
            self._flush_mirror()

    def _flush_mirror(self):
        """Flushes the mirror_buffer directly to local stdout."""
        if not self._mirror_buffer:
            return

        import sys
        try:
            os.write(sys.stdout.fileno(), self._mirror_buffer)
            self._mirror_buffer = b""
        except Exception as e:
            logger.debug(f"Failed to flush mirror buffer: {e}")
        finally:
            self._mirror_timer = None

    def _extract_safe_chunk(self) -> str:
        """
        Extracts part of self._buffer that is safe to send (no partial ANSI),
        leaving any partial sequence in the buffer.
        """
        if not self._buffer:
            return ""

        # Find the last ESC character
        last_esc = self._buffer.rfind("\x1b")
        
        if last_esc != -1:
            potential_seq = self._buffer[last_esc:]
            # If the sequence at the end is incomplete AND it doesn't 
            # already contain a complete sequence or extra text after a 
            # possible sequence, we treat it as partial.
            # A sequence is "truly partial" if it's just ESC or ESC+[...
            # and doesn't have a terminator yet.
            
            # Use search to see if there's any COMPLETE sequence in the potential suffix
            match = ANSI_RE.search(potential_seq)
            
            if match:
                # There is a complete sequence. 
                # Is there anything AFTER it?
                end_pos = match.end()
                if end_pos < len(potential_seq):
                    # There is text after the complete sequence. 
                    # Does THAT text contain another (partial) ESC?
                    remaining = potential_seq[end_pos:]
                    next_esc = remaining.rfind("\x1b")
                    if next_esc != -1:
                        # There's another ESC in the remainder
                        split_point = last_esc + end_pos + next_esc
                        to_write = self._buffer[:split_point]
                        self._buffer = self._buffer[split_point:]
                        return to_write
                    else:
                        # No more ESCs, it's all safe
                        pass
                else:
                    # Sequence ends exactly at buffer end, all safe
                    pass
            else:
                # No complete sequence found in the suffix starting with ESC.
                # If it's short, it's likely a partial sequence.
                if len(potential_seq) < 32:
                    to_write = self._buffer[:last_esc]
                    self._buffer = self._buffer[last_esc:]
                    return to_write
        
        to_write = self._buffer
        self._buffer = ""
        return to_write

    def prepare_terminal(self):
        """Clears terminal and sets local stdin to raw mode."""
        self._terminal_manager.prepare_terminal()

    def restore_terminal(self):
        """Restores the terminal to its original state."""
        self._terminal_manager.restore_terminal()

    async def _flush_buffer(self, items: list[str]):
        """Processes collected chunks, strips ANSI, and sends to Telegram."""
        if not items:
            return

        full_text = "".join(items)
        full_text = ANSI_RE.sub('', full_text)

        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        if not lines:
            return
            
        full_message = "\n".join(lines)

        MAX_TELEGRAM_MSG = 4096
        if len(full_message) > MAX_TELEGRAM_MSG:
            half_limit = (MAX_TELEGRAM_MSG // 2) - 100
            full_message = (
                full_message[:half_limit]
                + "\n\n... [Output trimmed due to size] ...\n\n"
                + full_message[-half_limit:]
            )

        try:
            await self._sender(full_message)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
