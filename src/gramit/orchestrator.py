import os
import pty
import asyncio
from typing import List


class Orchestrator:
    """
    Manages a child process within a pseudo-terminal (PTY).

    This class is responsible for spawning, monitoring, and interacting
    with a command-line application running in a PTY.
    """

    def __init__(self, command: List[str]):
        """
        Initializes the Orchestrator.

        Args:
            command: The command and its arguments to execute.
        """
        self._command = command
        self._pid: int | None = None
        self._master_fd: int | None = None

    async def read(self, max_bytes: int) -> bytes:
        """
        Reads data from the child process's stdout.

        Args:
            max_bytes: The maximum number of bytes to read.

        Returns:
            The data read from stdout as bytes.
        """
        if self._master_fd is None:
            return b""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, os.read, self._master_fd, max_bytes)

    async def write(self, data: str | bytes):
        """
        Writes data to the child process's stdin.

        Args:
            data: The string or bytes data to write.
        """
        if self._master_fd is not None:
            if isinstance(data, str):
                encoded_data = data.encode("utf-8")
            else:
                encoded_data = data
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.write, self._master_fd, encoded_data)

    async def start(self) -> int:
        """
        Spawns the child process in a new PTY, inheriting the current terminal size.

        Returns:
            The PID of the spawned process.
        """
        # Get current terminal size
        import shutil
        import struct
        import fcntl
        import termios
        import sys
        
        # Try to get size from stdout/stdin
        try:
            cols, rows = shutil.get_terminal_size()
        except Exception:
            cols, rows = 80, 24

        pid, master_fd = pty.fork()

        if pid == pty.CHILD:
            # In the child process, execute the command
            try:
                cmd = self._command[0]
                # If the command is not an absolute path and not in PATH,
                # but exists in the current directory, prepend ./
                if not os.path.isabs(cmd) and os.path.sep not in cmd:
                    if not shutil.which(cmd) and os.path.exists(cmd):
                        self._command[0] = os.path.join(os.curdir, cmd)
                
                os.execvp(self._command[0], self._command)
            except OSError as e:
                # If execvp fails, we need to exit the child process
                print(f"FATAL: execvp failed: {e}")
                os._exit(1)
        else:
            # In the parent process
            self._pid = pid
            self._master_fd = master_fd
            
            # Set initial size explicitly on the master FD
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
            except Exception:
                pass # Best effort

            return pid

    def resize(self):
        """
        Updates the child PTY's window size to match the current terminal size.
        """
        if self._master_fd is None:
            return

        import shutil
        import struct
        import fcntl
        import termios
        import sys

        try:
            # Use sys.stdout for size as it's most likely the TTY
            cols, rows = shutil.get_terminal_size()
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass # Best effort

    def is_alive(self) -> bool:
        """Checks if the child process is currently running."""
        if not self._pid:
            return False
        try:
            # waitpid with WNOHANG returns (0, 0) if the process is still running
            return os.waitpid(self._pid, os.WNOHANG) == (0, 0)
        except ChildProcessError:
            # This occurs if the process is already reaped
            return False

    async def shutdown(self):
        """Terminates the child process and closes the PTY."""
        if self.is_alive() and self._pid:
            try:
                os.kill(self._pid, 15)  # SIGTERM
                # Give it a moment to terminate gracefully
                await asyncio.sleep(0.1)
                if self.is_alive():
                    os.kill(self._pid, 9)  # SIGKILL
            except ProcessLookupError:
                # Process already died
                pass

        if self._master_fd:
            os.close(self._master_fd)

        self._pid = None
        self._master_fd = None
