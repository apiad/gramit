# Gramit Implementation Roadmap

This document outlines the development plan for Gramit, based on `DESIGN.md v2.1`. We will follow a phased approach, ensuring each component is tested and documented before moving to the next.

## Phase 1: Project Scaffolding & Core Dependencies

The goal of this phase is to set up a clean, professional Python project structure.

*   [x] Initialize the project with `uv`.
*   [x] Define project metadata and dependencies in `pyproject.toml`.
*   [x] Use `uv add` to bring in initial dependencies:
    *   [x] `python-dotenv` (for configuration)
    *   [x] `python-telegram-bot` (for Telegram API interaction)
    *   [x] `pytest` and `pytest-asyncio` (for testing)
*   [x] Create the basic source directory structure: `src/gramit/`.
*   [x] Create the basic test directory structure: `tests/`.
*   [x] Add initial empty files for core components (`orchestrator.py`, `router.py`, `telegram.py`, etc.) to `src/gramit/`.
*   [x] Configure `pytest` in `pyproject.toml` or `pytest.ini`.

## Phase 2: The PTY Orchestrator

This phase focuses on creating and managing a child process within a pseudo-terminal (PTY), removing the need for `tmux`.

*   [x] **Testing:**
    *   [x] Write a test for the PTY orchestrator that confirms a child process is spawned correctly in a PTY.
    *   [x] Write a test to verify that data written to the master PTY descriptor is received by the child's `stdin`.
    *   [x] Write a test to verify that data sent from the child's `stdout` is readable from the master PTY descriptor.
*   [x] **Implementation:**
    *   [x] Create an `Orchestrator` class that uses `os.forkpty()` to spawn the target command.
    *   [x] Implement methods to manage the lifecycle of the child process (e.g., `start`, `shutdown`, checking if it's alive).
*   [x] **Documentation:**
    *   [x] Write docstrings for the `Orchestrator` class and its public methods, explaining how it manages the PTY.

## Phase 3: The Output Router (Line Mode)

We'll build the line-based output handler and the core debouncing logic.

*   [x] **Testing:**
    *   [x] Write unit tests for the asynchronous `Debouncer` class. Ensure it collects items and only flushes them after the specified time interval has passed without new items.
    *   [x] Write a test for the `OutputRouter` in `line-mode`. This test should simulate PTY output, and assert that a mocked Telegram sending function is called by the debouncer with correctly buffered/aggregated line content.
*   [x] **Implementation:**
    *   [x] Implement the generic `AsyncDebouncer` class.
    *   [x] Implement the `OutputRouter` class. It should have a method to read from the PTY master descriptor asynchronously.
    *   [x] Implement the line-buffering logic for `line-mode`.
*   [x] **Documentation:**
    *   [x] Write docstrings for the `AsyncDebouncer` and the `OutputRouter`, detailing the line-mode logic.

## Phase 4: Input Router & End-to-End Integration

This phase connects Gramit to Telegram and wires all the components together into a functioning application for line-based commands.

*   [x] **Testing:**
    *   [x] Write an integration test for the `InputRouter`. Using a mock Telegram client, simulate receiving a message and verify that the text is correctly written to the PTY master descriptor.
    *   [x] Add a test case to ensure messages from unauthorized `chat_id`s are ignored.
*   [x] **Implementation:**
    *   [x] Create the `InputRouter` class, which initializes the `python-telegram-bot` client and sets up message handlers.
    *   [x] Implement the `chat_id` authorization check.
    *   [x] Create the main application entrypoint (`__main__.py` or `cli.py`).
    *   [x] Implement CLI argument parsing (`--chat-id`, `--line-mode`, `command`).
    *   [x] Implement loading of the `GRAMIT_TELEGRAM_TOKEN` from environment variables / `.env` file.
    *   [x] Write the main `async` function that initializes and runs the `Orchestrator`, `InputRouter`, and `OutputRouter` together.
*   [x] **Documentation:**
    *   [x] Document the application's configuration requirements (`GRAMIT_TELEGRAM_TOKEN`, `--chat-id`).
    *   [x] Create an initial `README.md` with basic setup and usage instructions.
*   [x] **Manual Verification:**
    *   [x] Run the application end-to-end with a simple command (e.g., `ping 8.8.8.8`) to confirm the `line-mode` integration is working.

## Phase 5: External Output Streaming

This phase adds support for tailing an external file for output, bypassing the PTY's output capture. This is useful for complex TUI applications that can write a clean log to a file.

*   [x] **Testing:**
    *   [x] Write unit tests for a `FileTailer` component that can asynchronously watch a file for new appends.
    *   [x] Write integration tests for the `OutputRouter` when in `output-stream` mode, ensuring it ignores PTY output and correctly routes file-tailed data.
*   [x] **Implementation:**
    *   [x] Implement a `FileTailer` class (or similar mechanism) that handles opening, seeking to end, and asynchronously reading new data from a file.
    *   [x] Add the `-o` / `--output-stream <FILE>` CLI argument to `cli.py`.
    *   [x] Update `OutputRouter` to support reading from either the `Orchestrator` (default) or the `FileTailer`.
    *   [x] Ensure the `Orchestrator` still manages the PTY for `stdin` even when the output is being tailed from a file.
*   [x] **Documentation:**
    *   [x] Document the `--output-stream` feature in the `README.md`.
    *   [x] Explain the use case for this mode (e.g., bridging TUI apps that have a "log to file" feature).
*   [x] **Manual Verification:**
    *   [x] Run `gramit -o test.log my_app` and verify that appends to `test.log` are sent to Telegram while `stdin` still works.

## Phase 6: Finalization & Packaging

This final phase polishes the project for release.

*   [x] **Implementation:**
    *   [x] Implement the `gramit --register` helper mode (replaces separate script).
    *   [x] Finalize `pyproject.toml` for packaging, defining the console script entry point for `gramit`.
    *   [x] Implement terminal size inheritance and dynamic resizing.
    *   [x] Robust terminal cleanup and restoration on exit.
    *   [x] Implement key shortcuts and modifier combinations (/enter, /ca, /c/sa, etc.).
    *   [x] Implement `--no-mirror` mode for silent local operation.
*   [x] **Documentation:**
    *   [x] Thoroughly update `README.md` with complete installation instructions, advanced usage, examples, and security warnings.
    *   [x] Ensure all public modules and functions have high-quality docstrings.
* [ ] **Final Review:**
    * [x] Review the entire codebase for clarity, consistency, and adherence to the design.
    * [x] Run all tests one last time.
    * [ ] Publish to PyPI.

