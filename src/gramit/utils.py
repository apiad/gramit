import shutil
import struct
import fcntl
import termios
import logging

# Configure logging for the project
logger = logging.getLogger("gramit")


def get_terminal_size(fallback=(80, 24)):
    """
    Retrieves the current terminal size (columns, rows).
    
    Args:
        fallback: A tuple (columns, rows) to use if size cannot be determined.
        
    Returns:
        A tuple (columns, rows).
    """
    try:
        # Try to get size from stdout as it's the most likely TTY
        size = shutil.get_terminal_size(fallback=fallback)
        return size.columns, size.lines
    except Exception as e:
        logger.debug(f"Failed to get terminal size: {e}")
        return fallback


def set_terminal_size(fd: int, cols: int, rows: int):
    """
    Sets the window size for a given file descriptor (PTY master).
    
    Args:
        fd: The file descriptor to update.
        cols: Number of columns.
        rows: Number of rows.
    """
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception as e:
        logger.debug(f"Failed to set terminal size on fd {fd}: {e}")
