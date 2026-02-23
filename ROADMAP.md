# Gramit Implementation Roadmap

This document outlines the development plan for Gramit, based on `DESIGN.md v2.1`. We will follow a phased approach, ensuring each component is tested and documented before moving to the next.

## Phase 1: Project Scaffolding & Core Dependencies

The goal of this phase is to set up a clean, professional Python project structure.

*   [x] Initialize the project with `uv`.
*   [x] Define project metadata and dependencies in `pyproject.toml`.
*   [x] Use `uv add` to bring in initial dependencies:
    *   [x] `python-dotenv` (for configuration)
    *   [x] `pyte` (for TUI mode screen emulation)
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

Before tackling the complexity of TUIs, we'll build the simpler line-based output handler and the core debouncing logic.

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

## Phase 5: The Output Router (TUI Mode)

This is the most complex phase, where we add support for capturing and cleaning TUI applications.

*   [ ] **Testing:**
    *   [ ] Write unit tests for the `HeuristicFilter`. Create sample TUI screen strings and assert that box-drawing characters, menu bars, and excess whitespace are correctly removed.
    *   [ ] Write a new test for the `OutputRouter` in `TUI-mode`. It should feed a byte stream with ANSI escape codes to the router and assert that the `pyte` screen's text dump is correctly passed to the filter and then to the mocked Telegram sender.
*   [ ] **Implementation:**
    *   [ ] Implement the `HeuristicFilter` module with functions for cleaning the screen dump.
    *   [ ] Integrate `pyte` into the `OutputRouter`. The router should now feed all PTY output into a `pyte.Stream` object.
    *   [ ] Implement the snapshotting logic that dumps the `pyte` screen's display text.
    *   [ ] Add the logic to the `OutputRouter` to use the `HeuristicFilter` on the screen snapshot before sending.
    *   [ ] Connect the `--line-mode` CLI flag to switch between the two routing modes.
*   [ ] **Documentation:**
    *   [ ] Document the `TUI-mode` functionality in the `OutputRouter` docstrings.
    *   [ ] Explain the purpose and limitations of the `HeuristicFilter`.
*   [ ] **Manual Verification:**
    *   [ ] Run the application end-to-end with a TUI application (e.g., `htop`, `apt`) to confirm TUI mode is working as expected.

## Phase 6: Finalization & Packaging

This final phase polishes the project for release.

*   [ ] **Implementation:**
    *   [ ] Create the `gramit-get-chat-id` helper script.
    *   [ ] Finalize `pyproject.toml` for packaging, defining the console script entry points for `gramit` and `gramit-get-chat-id`.
*   [ ] **Documentation:**
    *   [ ] Thoroughly update `README.md` with complete installation instructions, advanced usage, examples for both modes, and troubleshooting tips.
    *   [ ] Write the final `CHANGELOG.md` entry for the first release.
    *   [ ] Ensure all public modules and functions have high-quality docstrings.
*   [ ] **Final Review:**
    *   [ ] Review the entire codebase for clarity, consistency, and adherence to the design.
    *   [ ] Run all tests one last time.
    *   [ ] Consider publishing to TestPyPI before a final release to PyPI.
