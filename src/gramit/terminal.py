import os
import sys
import tty
import termios
import io
import time
import subprocess
from .utils import logger

# ANSI Escape Sequences
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


class TerminalManager:
    """
    Manages local terminal state, including raw mode and screen restoration.
    """

    def __init__(self, enabled: bool = True):
        """
        Initializes the TerminalManager.

        Args:
            enabled: Whether terminal management is enabled.
        """
        self._enabled = enabled
        self._old_settings = None
        self._restored = False

    def prepare_terminal(self):
        """
        Clears the terminal and sets local stdin to raw mode.
        """
        if not self._enabled:
            return

        try:
            fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
        except (Exception, io.UnsupportedOperation):
            self._old_settings = None

        try:
            os.write(sys.stdout.fileno(), (CLEAR_SCREEN + HOME_CURSOR).encode("ascii"))
        except Exception as e:
            logger.debug(f"Failed to clear terminal: {e}")

    def restore_terminal(self):
        """
        Restores the terminal to its original state.
        Ensures restoration happens only once.
        """
        if not self._enabled or self._restored:
            return

        self._restored = True
        
        try:
            fd = sys.stdin.fileno()
            if self._old_settings:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)
                except Exception:
                    pass
        except (Exception, io.UnsupportedOperation):
            pass

        try:
            os.write(sys.stdout.fileno(), RESTORE_TERMINAL_SEQ)
        except Exception as e:
            logger.debug(f"Failed to write restoration sequence: {e}")
        
        # Settle time and flush
        time.sleep(0.1)

        try:
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        except Exception:
            pass

        try:
            subprocess.run(["stty", "sane"], check=False, capture_output=True)
        except Exception:
            pass
