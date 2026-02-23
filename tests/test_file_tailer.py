import asyncio
import pytest
from gramit.router import FileTailer

@pytest.mark.asyncio
async def test_file_tailer_reads_new_appends(tmp_path):
    """
    Tests that FileTailer correctly identifies and yields data appended to a file.
    """
    test_file = tmp_path / "test.log"
    # Create file
    test_file.write_text("initial content\n")
    
    tailer = FileTailer(str(test_file), poll_interval=0.01)
    
    results = []
    
    # Mock orchestrator
    from unittest.mock import MagicMock
    mock_orchestrator = MagicMock()
    mock_orchestrator.is_alive.return_value = True

    async def run_tailer():
        async for line in tailer.read_new(mock_orchestrator):
            results.append(line)
            if len(results) == 2:
                tailer.stop()

    # Start tailer in the background
    tailer_task = asyncio.create_task(run_tailer())
    
    # Wait a bit to ensure tailer reached the end
    await asyncio.sleep(0.1)
    with open(test_file, "a") as f:
        f.write("new line 1\n")
        f.flush()
        await asyncio.sleep(0.05)
        f.write("new line 2\n")
        f.flush()

    # Wait for tailer to finish
    await asyncio.wait_for(tailer_task, timeout=2.0)
    
    assert results == ["new line 1\n", "new line 2\n"]
    # Verify it didn't read 'initial content'
    assert "initial content\n" not in results

@pytest.mark.asyncio
async def test_file_tailer_waits_for_file_creation(tmp_path):
    """
    Tests that FileTailer waits for a file to be created if it doesn't exist.
    """
    test_file = tmp_path / "delayed.log"
    tailer = FileTailer(str(test_file), poll_interval=0.01)
    
    results = []
    
    # Mock orchestrator
    from unittest.mock import MagicMock
    mock_orchestrator = MagicMock()
    mock_orchestrator.is_alive.return_value = True

    async def run_tailer():
        async for line in tailer.read_new(mock_orchestrator):
            results.append(line)
            if len(results) == 1:
                tailer.stop()

    tailer_task = asyncio.create_task(run_tailer())
    
    # Wait a bit before creating the file
    await asyncio.sleep(0.1)
    
    # Writing the file should trigger the tailer. 
    # To be safe, we create it empty first, then append.
    test_file.write_text("")
    await asyncio.sleep(0.1)
    with open(test_file, "a") as f:
        f.write("first line\n")
        f.flush()
    
    await asyncio.wait_for(tailer_task, timeout=2.0)
    assert results == ["first line\n"]
