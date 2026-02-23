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

    async def read_new(self, orchestrator: Orchestrator):
        """
        A generator that yields new content appended to the file.
        Wait for the file to be created if it doesn't exist yet.
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
            except Exception:
                await asyncio.sleep(self._poll_interval)
                continue

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
        # Prepare terminal for mirroring
        self._prepare_terminal()

        # Always drain the PTY to mirror to local terminal and prevent blocking.
        pty_drainer = asyncio.create_task(self._drain_pty())

        if self._output_stream:
            self._tailer = FileTailer(self._output_stream)
            try:
                async for data in self._tailer.read_new(self._orchestrator):
                    await self._process_line_mode(data)
                    # Push to debouncer
                    if self._buffer:
                        await self._debouncer.push(self._buffer)
                        self._buffer = ""
            except asyncio.CancelledError:
                pass
            finally:
                if self._tailer:
                    self._tailer.stop()
        else:
            # Standard PTY -> Telegram mode
            while self._orchestrator.is_alive():
                try:
                    # Non-blocking read attempt
                    data = await self._orchestrator.read(1024)
                    if not data:
                        # Might be EOF or just temporary no-data
                        if not self._orchestrator.is_alive():
                            break
                        await asyncio.sleep(0.05)
                        continue
                    
                    # Mirror to local
                    import sys
                    sys.stdout.write(data)
                    sys.stdout.flush()

                    await self._process_line_mode(data)
                    if self._buffer:
                        await self._debouncer.push(self._buffer)
                        self._buffer = ""

                except asyncio.CancelledError:
                    break
                except Exception:
                    break
        
        # Cleanup drainer
        if not pty_drainer.done():
            pty_drainer.cancel()
            try:
                await pty_drainer
            except asyncio.CancelledError:
                pass

        # Final flushes for any remaining data
        if self._buffer:
            await self._debouncer.push(self._buffer)
            self._buffer = ""
        await self._debouncer.flush()
        
        # Restore terminal state in case it was a TUI
        self._restore_terminal()

    def _prepare_terminal(self):
        """
        Clears the terminal and moves cursor to home before mirroring.
        """
        import sys
        # \x1b[2J: clear screen, \x1b[H: home cursor
        sys.stdout.write("\x1b[2J\x1b[H")
        sys.stdout.flush()

    def _restore_terminal(self):
        """
        Sends ANSI escape sequences to disable mouse tracking, 
        exit alternate screen buffer, and clear the screen.
        """
        import sys
        # Disable various mouse tracking modes
        # ?1000l: VT200, ?1002l: Button event, ?1003l: Any event, ?1006l: SGR
        # ?1049l: Exit alternate screen
        # \x1b[2J\x1b[H: Clear and home
        sequences = "\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1049l\x1b[2J\x1b[H"
        sys.stdout.write(sequences)
        sys.stdout.flush()
        
        # Also try to run stty sane to be extra sure
        import subprocess
        try:
            subprocess.run(["stty", "sane"], check=False, capture_output=True)
        except Exception:
            pass

    async def _drain_pty(self):
        """
        Mirror PTY to local stdout. Only used if output_stream is active.
        """
        if not self._output_stream:
            return

        import sys
        while self._orchestrator.is_alive():
            try:
                data = await self._orchestrator.read(1024)
                if not data:
                    if not self._orchestrator.is_alive():
                        break
                    await asyncio.sleep(0.05)
                    continue
                sys.stdout.write(data)
                sys.stdout.flush()
            except (asyncio.CancelledError, OSError, EOFError):
                break
            except Exception:
                break

    async def _process_line_mode(self, data: str):
        # Accumulate in buffer
        self._buffer += data

    async def _flush_buffer(self, items: list[str]):
        if not items:
            return

        full_text = "".join(items)
        # Split into lines and filter empty ones
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        
        if not lines:
            return
            
        full_message = "\n".join(lines)

        # Telegram message limit is 4096 characters
        MAX_TELEGRAM_MSG = 4096
        if len(full_message) > MAX_TELEGRAM_MSG:
            half_limit = (MAX_TELEGRAM_MSG // 2) - 50
            full_message = (
                full_message[:half_limit]
                + "\n\n... [Output trimmed due to size] ...\n\n"
                + full_message[-half_limit:]
            )

        await self._sender(full_message)
