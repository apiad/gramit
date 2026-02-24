from collections import namedtuple
from unittest.mock import patch
import struct
import termios

from gramit.utils import get_terminal_size, set_terminal_size

# Mock terminal size namedtuple
TerminalSize = namedtuple("terminal_size", ["columns", "lines"])

def test_get_terminal_size_success():
    # Mock shutil.get_terminal_size to return a known size
    with patch("shutil.get_terminal_size") as mock_get_size:
        mock_get_size.return_value = TerminalSize(100, 50)
        cols, rows = get_terminal_size()
        assert cols == 100
        assert rows == 50

def test_get_terminal_size_fallback():
    # Mock shutil.get_terminal_size to raise an exception
    with patch("shutil.get_terminal_size", side_effect=Exception("Error")):
        cols, rows = get_terminal_size(fallback=(80, 24))
        assert cols == 80
        assert rows == 24

def test_set_terminal_size():
    mock_fd = 123
    cols, rows = 120, 40
    expected_winsize = struct.pack("HHHH", rows, cols, 0, 0)
    
    with patch("fcntl.ioctl") as mock_ioctl:
        set_terminal_size(mock_fd, cols, rows)
        mock_ioctl.assert_called_once_with(mock_fd, termios.TIOCSWINSZ, expected_winsize)
