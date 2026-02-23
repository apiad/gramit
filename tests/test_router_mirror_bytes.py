import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from gramit.router import OutputRouter

@pytest.mark.asyncio
async def test_handle_new_data_with_bytes():
    # Mock Orchestrator
    orchestrator = MagicMock()
    orchestrator.is_alive.side_effect = [True, False]
    # orchestrator.read returns bytes
    orchestrator.read = AsyncMock(return_value=b"hello")
    
    # Mock sender
    sender = AsyncMock()
    
    router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        mirror=True
    )
    
    # We want to test _handle_new_data specifically
    # It's an async function
    try:
        await router._handle_new_data(b"some bytes")
    except TypeError as e:
        pytest.fail(f"_handle_new_data failed with TypeError: {e}")
    except Exception as e:
        pytest.fail(f"_handle_new_data failed with unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_handle_new_data_with_bytes())
