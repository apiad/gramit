import shutil
import struct
import fcntl
import termios
import logging

# Configure logging for the project
logger = logging.getLogger("gramit")

# ANSI Escape Sequences
# CSI (Control Sequence Introducer)
ESC = "\x1b"
CSI = ESC + "["

# Terminal State Control
CLEAR_SCREEN = CSI + "2J"
HOME_CURSOR = CSI + "H"
SHOW_CURSOR = CSI + "25h"
HIDE_CURSOR = CSI + "25l"
ENTER_ALT_SCREEN = CSI + "?1049h"
EXIT_ALT_SCREEN = CSI + "?1049l"

# Mouse Tracking (Disable sequences)
DISABLE_MOUSE_VT200 = CSI + "?1000l"
DISABLE_MOUSE_BUTTON = CSI + "?1002l"
DISABLE_MOUSE_ANY = CSI + "?1003l"
DISABLE_MOUSE_SGR = CSI + "?1006l"

# Combined Restoration Sequence
RESTORE_TERMINAL_SEQ = (
    DISABLE_MOUSE_VT200 +
    DISABLE_MOUSE_BUTTON +
    DISABLE_MOUSE_ANY +
    DISABLE_MOUSE_SGR +
    EXIT_ALT_SCREEN +
    SHOW_CURSOR +
    CLEAR_SCREEN +
    HOME_CURSOR
).encode("ascii")


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
