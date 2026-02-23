import pytest
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
