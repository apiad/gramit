from unittest.mock import patch
from gramit.terminal import TerminalManager, RESTORE_TERMINAL_SEQ

def test_terminal_manager_enabled_false():
    """
    Ensures TerminalManager does nothing when disabled.
    """
    manager = TerminalManager(enabled=False)
    with patch("termios.tcgetattr") as mock_getattr:
        manager.prepare_terminal()
        mock_getattr.assert_not_called()
    
    with patch("os.write") as mock_write:
        manager.restore_terminal()
        mock_write.assert_not_called()

def test_terminal_manager_prepare_and_restore():
    """
    Tests that TerminalManager correctly prepares and restores the terminal.
    """
    manager = TerminalManager(enabled=True)
    
    # Mocking necessary parts for terminal handling
    with (
        patch("sys.stdin.fileno") as mock_fileno,
        patch("termios.tcgetattr") as mock_getattr,
        patch("termios.tcsetattr") as mock_setattr,
        patch("tty.setraw") as mock_setraw,
        patch("os.write") as mock_write,
        patch("termios.tcflush") as mock_flush,
        patch("subprocess.run") as mock_run,
    ):
        mock_fileno.return_value = 0
        mock_getattr.return_value = ["old_settings"]
        
        manager.prepare_terminal()
        
        assert mock_getattr.called
        assert mock_setraw.called
        # Check if it cleared the screen
        assert mock_write.called
        
        manager.restore_terminal()
        
        assert mock_setattr.called
        # Restoration sequence should be written
        written_data = b"".join(call.args[1] for call in mock_write.call_args_list)
        assert RESTORE_TERMINAL_SEQ in written_data
        
        assert mock_flush.called
        assert mock_run.called

def test_terminal_manager_restore_only_once():
    """
    Verifies that TerminalManager restore_terminal only performs restoration once.
    """
    manager = TerminalManager(enabled=True)
    
    with (
        patch("termios.tcgetattr"),
        patch("termios.tcsetattr"),
        patch("tty.setraw"),
        patch("os.write") as mock_write,
        patch("termios.tcflush"),
        patch("subprocess.run"),
    ):
        manager.prepare_terminal()
        manager.restore_terminal()
        
        first_call_count = mock_write.call_count
        
        manager.restore_terminal()
        # Should NOT have increased
        assert mock_write.call_count == first_call_count
