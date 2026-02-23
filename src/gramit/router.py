import asyncio
import os
import re
from typing import Callable, Coroutine, Any, Optional

from .orchestrator import Orchestrator
from .debouncer import AsyncDebouncer

# Regex for matching ANSI escape sequences (CSI, OSC, etc.)
# This is a broad regex to capture most common sequences
ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


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
        mirror: bool = True,
    ):
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
        self._old_settings = None
        self._mirror_timer: Optional[asyncio.TimerHandle] = None
        self._mirror_debounce_interval = 0.04 # 40ms for better TUI quiescence (approx 25fps)

    async def start(self):
        """
        Starts the main loop to read and route output.
        """
        # Prepare terminal for mirroring
        if self._mirror:
            self._prepare_terminal()

        # Always drain the PTY to mirror to local terminal (if enabled) and prevent blocking.
        pty_drainer = asyncio.create_task(self._drain_pty())
        
        # Local input handler
        local_input_handler = None
        if self._mirror:
            local_input_handler = asyncio.create_task(self._handle_local_input())

        try:
            if self._output_stream:
                self._tailer = FileTailer(self._output_stream)
                try:
                    # FileTailer.read_new yields chunks of text
                    async for data in self._tailer.read_new(self._orchestrator):
                        await self._handle_new_data(data)
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
                        data = await self._orchestrator.read(4096)
                        if not data:
                            # Might be EOF or just temporary no-data
                            if not self._orchestrator.is_alive():
                                break
                            await asyncio.sleep(0.01)
                            continue
                        
                        await self._handle_new_data(data)

                    except asyncio.CancelledError:
                        break
                    except Exception:
                        break
        finally:
            # Cleanup tasks
            for task in [pty_drainer, local_input_handler]:
                if task and not task.done():
                    task.cancel()
            
            # Final flushes for any remaining data
            if self._buffer:
                await self._debouncer.push(self._buffer)
                self._buffer = ""
            
            # For mirror, we flush one last time immediately
            if self._mirror_buffer:
                self._flush_mirror()
                
            await self._debouncer.flush()
            
            # Restore terminal state in case it was a TUI
            if self._mirror:
                self._restore_terminal()

    async def _handle_new_data(self, data: str | bytes):
        """
        Handles incoming data by appending it to buffers and triggering
        flushes for both mirror and Telegram.
        """
        # 1. Local Mirror (accumulate as bytes and debounce)
        if self._mirror:
            if isinstance(data, str):
                self._mirror_buffer += data.encode('utf-8', errors='replace')
            else:
                self._mirror_buffer += data
            self._schedule_mirror_flush()
            
        # 2. Telegram (safe chunks only)
        if isinstance(data, bytes):
            # Decode for Telegram processing
            text = data.decode('utf-8', errors='replace')
        else:
            text = data

        self._buffer += text
        safe_chunk = self._extract_safe_chunk()
        if safe_chunk:
            await self._debouncer.push(safe_chunk)

    def _schedule_mirror_flush(self):
        """
        Schedules a flush to the local terminal.
        """
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
        """
        Flushes the current mirror_buffer to local stdout. 
        Uses a slightly longer debounce and direct writing to minimize flickering.
        """
        if not self._mirror_buffer:
            return

        import sys
        # Use os.write for direct, non-buffered output
        try:
            os.write(sys.stdout.fileno(), self._mirror_buffer)
            self._mirror_buffer = b""
        except Exception:
            pass
        finally:
            self._mirror_timer = None

    def _extract_safe_chunk(self) -> str:
        """
        Extracts the part of self._buffer that is safe to send (no partial ANSI),
        leaving the partial sequence in the buffer.
        """
        if not self._buffer:
            return ""

        # Look for partial ANSI escape sequences at the end of the buffer
        # A sequence starts with ESC (\x1b)
        last_esc = self._buffer.rfind("\x1b")
        
        if last_esc != -1:
            # We found an escape character. Check if the sequence is complete.
            potential_seq = self._buffer[last_esc:]
            # If the sequence is incomplete, we split the buffer
            if not ANSI_RE.fullmatch(potential_seq) and len(potential_seq) < 32:
                # Extract everything up to the ESC, keep the rest for later
                to_write = self._buffer[:last_esc]
                self._buffer = self._buffer[last_esc:]
                return to_write
        
        # No partial sequence or complete sequence at the end
        to_write = self._buffer
        self._buffer = ""
        return to_write

    def _prepare_terminal(self):
        """
        Clears the terminal and sets it to raw mode for local input.
        """
        import sys
        import tty
        import termios
        import io
        
        # Save original attributes for restoration
        try:
            fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
        except (Exception, io.UnsupportedOperation):
            self._old_settings = None

        # \x1b[2J: clear screen, \x1b[H: home cursor
        try:
            os.write(sys.stdout.fileno(), b"\x1b[2J\x1b[H")
        except Exception:
            pass

    def _restore_terminal(self):
        """
        Restores the terminal to its original state.
        """
        import sys
        import termios
        import io
        
        # Restore raw mode first
        try:
            fd = sys.stdin.fileno()
            if self._old_settings:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)
                except Exception:
                    pass
        except (Exception, io.UnsupportedOperation):
            pass

        # Disable various mouse tracking modes
        # ?1000l: VT200, ?1002l: Button event, ?1003l: Any event, ?1006l: SGR
        # ?1049l: Exit alternate screen
        # ?25h: Show cursor
        sequences = b"\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1049l\x1b[?25h"
        try:
            os.write(sys.stdout.fileno(), sequences)
        except Exception:
            pass
        
        # Give the terminal emulator a tiny bit of time to process the 
        # sequences and stop sending events before we flush.
        import time
        time.sleep(0.1)

        # Flush stdin to get rid of any mouse movement/click sequences 
        try:
            termios.tcflush(fd, termios.TCIFLUSH)
        except Exception:
            pass

        # Also try to run stty sane to be extra sure
        import subprocess
        try:
            subprocess.run(["stty", "sane"], check=False, capture_output=True)
        except Exception:
            pass

    async def _drain_pty(self):
        """
        Drain PTY and mirror to local stdout if enabled.
        Only runs if output_stream is active (as the main loop handles standard mode).
        """
        if not self._output_stream:
            return

        while self._orchestrator.is_alive():
            try:
                data = await self._orchestrator.read(1024)
                if not data:
                    if not self._orchestrator.is_alive():
                        break
                    await asyncio.sleep(0.05)
                    continue
                
                await self._handle_new_data(data)
            except (asyncio.CancelledError, OSError, EOFError):
                break
            except Exception:
                break

    async def _handle_local_input(self):
        """
        Reads from local stdin and writes to the orchestrator.
        """
        import sys
        import select
        loop = asyncio.get_running_loop()
        fd = sys.stdin.fileno()
        
        while self._orchestrator.is_alive():
            try:
                # Use select to wait for input with a timeout
                # This makes the loop responsive to process death and cancellation
                r, _, _ = await loop.run_in_executor(None, select.select, [fd], [], [], 0.5)
                if not r:
                    continue
                
                # Read as much as available to handle escape sequences and fast typing
                data = os.read(fd, 4096)
                if not data:
                    break
                await self._orchestrator.write(data)
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def _flush_buffer(self, items: list[str]):
        if not items:
            return

        full_text = "".join(items)
        
        # Strip ANSI escape sequences for Telegram output
        full_text = ANSI_RE.sub('', full_text)

        # Split into lines and filter empty ones
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        
        if not lines:
            return
            
        full_message = "\n".join(lines)

        # Telegram message limit is 4096 characters
        MAX_TELEGRAM_MSG = 4096
        if len(full_message) > MAX_TELEGRAM_MSG:
            # Trim the message if it's too long
            # Keep the beginning and the end, with a warning in the middle
            half_limit = (MAX_TELEGRAM_MSG // 2) - 50
            full_message = (
                full_message[:half_limit]
                + "\n\n... [Output trimmed due to size] ...\n\n"
                + full_message[-half_limit:]
            )

        await self._sender(full_message)
