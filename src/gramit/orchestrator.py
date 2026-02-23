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

    async def read(self, max_bytes: int) -> str:
        """
        Reads data from the child process's stdout.

        Args:
            max_bytes: The maximum number of bytes to read.

        Returns:
            The data read from stdout as a string.
        """
        if self._master_fd is None:
            return ""
        
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, os.read, self._master_fd, max_bytes)
        return data.decode('utf-8', errors='replace')

    async def write(self, data: str):
        """
        Writes data to the child process's stdin.

        Args:
            data: The string data to write.
        """
        if self._master_fd is not None:
            encoded_data = data.encode('utf-8')
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.write, self._master_fd, encoded_data)

    async def start(self) -> int:
        """
        Spawns the child process in a new PTY.

        Returns:
            The PID of the spawned process.
        """
        pid, master_fd = pty.fork()

        if pid == pty.CHILD:
            # In the child process, execute the command
            try:
                os.execvp(self._command[0], self._command)
            except OSError as e:
                # If execvp fails, we need to exit the child process
                print(f"FATAL: execvp failed: {e}")
                os._exit(1)
        else:
            # In the parent process
            self._pid = pid
            self._master_fd = master_fd
            return pid

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
