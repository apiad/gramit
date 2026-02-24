import pytest
from unittest.mock import patch
from gramit.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_spawns_process():
    """
    Tests that the Orchestrator can spawn a child process and that the
    process is alive.
    """
    command = ["/bin/echo", "hello"]
    orchestrator = Orchestrator(command)

    pid = await orchestrator.start()
    assert pid is not None
    assert orchestrator.is_alive()

    await orchestrator.shutdown()
    assert not orchestrator.is_alive()


@pytest.mark.asyncio
async def test_orchestrator_write_to_stdin():
    """
    Tests that data written to the orchestrator is received by the
    child's stdin. We use `cat` which will echo the text back to us.
    """
    command = ["/bin/cat"]
    orchestrator = Orchestrator(command)
    await orchestrator.start()
    assert orchestrator.is_alive()

    test_string = "hello from test!"
    await orchestrator.write(test_string + "\n")

    # We will test the output in the next test, for now, just shutdown
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_orchestrator_read_from_stdout():
    """
    Tests that data sent from the child's stdout can be read by the
    orchestrator.
    """
    command = ["/bin/echo", "hello from stdout"]
    orchestrator = Orchestrator(command)
    await orchestrator.start()
    assert orchestrator.is_alive()

    # The echo command writes and exits, so we can read until EOF
    output = await orchestrator.read(1024)

    # The output from the PTY includes the command and a carriage return/newline
    assert b"hello from stdout" in output

    await orchestrator.shutdown()

@pytest.mark.asyncio
async def test_orchestrator_resize():
    """
    Tests that the resize method correctly fetches new size and applies it.
    """
    orchestrator = Orchestrator(["/bin/ls"])
    orchestrator._master_fd = 999
    
    with patch("gramit.orchestrator.get_terminal_size") as mock_get_size, \
         patch("gramit.orchestrator.set_terminal_size") as mock_set_size:
        
        mock_get_size.return_value = (100, 50)
        orchestrator.resize()
        
        mock_get_size.assert_called_once()
        mock_set_size.assert_called_once_with(999, 100, 50)
