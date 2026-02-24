import json
import subprocess
import os
import pytest

LOG_FILE = "test_gemini.log"
HOOK_SCRIPT = ".gemini/hooks/gemini_logger.py"

@pytest.fixture
def clean_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    yield
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def run_hook(data):
    env = os.environ.copy()
    env["GEMINI_LOG_FILE"] = LOG_FILE
    
    process = subprocess.Popen(
        ["python3", HOOK_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    stdout, stderr = process.communicate(input=json.dumps(data))
    return stdout, stderr

def test_session_start_date_format(clean_log):
    data = {"hook_event_name": "SessionStart"}
    run_hook(data)
    with open(LOG_FILE, "r") as f:
        content = f.read()
    assert "--- Session Started (" in content
    # Check for the %YY bug (should NOT contain 2026Y)
    assert "2026Y" not in content

def test_streaming_chunks(clean_log):
    chunk1 = {
        "hook_event_name": "AfterModel",
        "llm_response": {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Hello "}]},
                    "finishReason": None
                }
            ]
        }
    }
    chunk2 = {
        "hook_event_name": "AfterModel",
        "llm_response": {
            "candidates": [
                {
                    "content": {"parts": [{"text": "world!"}]},
                    "finishReason": "STOP"
                }
            ]
        }
    }

    run_hook(chunk1)
    run_hook(chunk2)

    with open(LOG_FILE, "r") as f:
        content = f.read()
    
    # It should be "Hello world!\n\n"
    # Current behavior will likely produce "Hello \n\nworld!\n\n"
    assert content == "Hello world!\n\n"

def test_newline_stripping_trailing(clean_log):
    chunk1 = {
        "hook_event_name": "AfterModel",
        "llm_response": {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Hello\n"}]},
                    "finishReason": None
                }
            ]
        }
    }
    chunk2 = {
        "hook_event_name": "AfterModel",
        "llm_response": {
            "candidates": [
                {
                    "content": {"parts": [{"text": "World"}]},
                    "finishReason": "STOP"
                }
            ]
        }
    }
    run_hook(chunk1)
    run_hook(chunk2)
    with open(LOG_FILE, "r") as f:
        content = f.read()
    # Current behavior: "HelloWorld\n\n" (because chunk1's \n is stripped and chunk1 adds \n\n, and chunk2 adds \n\n)
    # Actually current behavior would be "Hello\n\nWorld\n\n" because \n\n is added to each chunk.
    # Correct behavior: "Hello\nWorld\n\n"
    assert content == "Hello\nWorld\n\n"
