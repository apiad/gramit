# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Documentation Enhancements:**
    - Added a comprehensive "Magical Use Cases" section to `README.md` featuring diverse scenarios for DevOps, AI agents (monitoring while cooking), and mobile productivity (Obsidian integration).
    - Added PyPI version and monthly download count badges to the top of `README.md`.

### Changed
- **Telegram Output Formatting:**
    - Removed automatic code block wrapping (triple backticks) from Telegram messages to support standard Markdown rendering.
    - Enabled `parse_mode="Markdown"` for all outgoing Telegram messages.
    - Refactored `/help`, `/quit`, and startup messages to use Markdown formatting (italics and inline code) instead of plain text or forced code blocks.
    - Removed the logic that escaped triple backticks in output messages.

### Fixed
- **Gemini Logger Hook:**
    - Fixed a bug where `transcript_data` was being treated as a `list` when it is now provided as a `dict` by the CLI, causing the hook to return early.
    - Implemented robust data extraction to locate conversation messages within the `messages`, `transcript`, or `history` keys of the transcript dictionary.
    - Added comprehensive internal debug logging to `gemini.log` to trace hook execution, event triggers, and data structure mismatches.

## [v0.4.6] - 2026-02-23

### Fixed
- **Gemini Logger Hook:** Fixed multiple bugs in the `gemini_logger.py` hook:
    - Corrected an invalid date format (`%YY` -> `%Y`) in the session start header.
    - Removed aggressive newline stripping from model response parts, preserving intended formatting.
    - Fixed a bug where double newlines were being appended after every streaming chunk, causing fragmented log entries.
    - The hook now correctly identifies the end of a model response (via `finishReason`) before appending paragraph separators.

## [v0.4.5] - 2026-02-23

## [v0.4.4] - 2026-02-23

## [v0.4.3] - 2026-02-23

## [v0.4.2] - 2026-02-23

### Fixed
- **ANSI Splitting:** Implemented `_extract_safe_chunk` to ensure partial ANSI escape sequences are not split between messages, preventing "glitchy" characters in Telegram and the local mirror.
- **Output Cleaning:** Added automatic stripping of ANSI escape sequences for Telegram output, significantly reducing "flicker" and noise in complex TUIs.
- **Redundancy:** Removed unused `_process_line_mode` and refactored the main routing loop for better robustness.

## [v0.4.1]

### Added
- **Expanded Key Support:** Added support for additional terminal keys: `Home`, `End`, `Page Up`, `Page Down`, `Insert`, and `F1` through `F12`.
- **New /help Command:** Added a `/help` Telegram command to list all available key shortcuts and modifier syntax.
- **Enhanced Key Test TUI:** Updated the `key_test_tui.py` example to show the newly supported keys in its footer for easier testing.
- **Robust Key Parsing:** Improved the internal key parsing logic to dynamically check for base key mappings, making the shortcut system more flexible.

## [v0.4.0]

### Added
- **No-Mirror Mode:** Added `--no-mirror` flag to silence local terminal output while bridging to Telegram. This is useful for background operations or when the host terminal shouldn't be disturbed.

## [v0.3.1]

### Security
- **Credential Leak Fix:** Removed an accidental Telegram token from the `README.md`.
- **Minor Fixes:** General codebase stabilization.

## [v0.3.0]

### Changed
- **Version Bump:** Synchronized project versioning for initial beta stability.

## [v0.2.0]

### Added
- **External Output Streaming:** New `-o` / `--output-stream` option to "tail" a file for output instead of capturing PTY stdout. This allows clean bridging of complex TUI applications.
- **Key Shortcuts & Modifiers:** Support for sending special keys (`/enter`, `/esc`, `/up`, etc.) and modifier combinations (e.g., `/c a` for Ctrl+A, `/c /s a` for Ctrl+Shift+A) from Telegram using an intuitive space-separated syntax.
- **Terminal Size Inheritance:** Child processes now inherit the terminal size of the host on startup.
- **Dynamic Resizing:** Added support for propagating `SIGWINCH` signals, ensuring TUI applications resize correctly with the terminal window.
- **Local Mirroring:** Gramit now mirrors the child process output to the local terminal, allowing for direct monitoring.
- **TUI-Friendly Examples:** Added `examples/tui_echo_with_log.py` (using `textual`) to demonstrate and test the output streaming feature.
- **Project Metadata:** Enhanced `pyproject.toml` with keywords, classifiers, and project URLs.

### Security
- **Security Audit:** Conducted a comprehensive audit and documented findings.
- **Permission Hardening:** Enforced owner-only permissions (`600`) for the `.env` file.
- **Input Rate Limiting:** Implemented `max_buffer_size` in `AsyncDebouncer` to prevent memory exhaustion from talkative processes.
- **Output Trimming:** `OutputRouter` now automatically trims overly large messages (exceeding Telegram's 4096-char limit) in the middle.
- **Security Warnings:** Added a prominent caution to `README.md` about the risks of remote shell access.

### Fixed
- **Terminal Corruption:** Implemented robust terminal restoration on exit, including disabling mouse tracking and exiting alternate screens.
- **Input Leakage:** Added `tcflush` with a safety delay to purge lingering ANSI mouse events from the input buffer.
- **Process Blocking:** Fixed a bug where processes would block if their stdout wasn't being drained when in `output-stream` mode.
- **Input Compatibility:** Changed Telegram input suffix from `\n` to `\r` for better compatibility with TUI app prompts.
- **Path Resolution:** Fixed `execvp` permission denied errors by automatically checking the current directory for local scripts.
- **Missing f-strings:** Fixed multiple instances of missing f-string prefixes in log statements.

## [v0.1.2]

### Security
- Implemented rate-limiting and output trimming in `OutputRouter` and `AsyncDebouncer` to prevent memory exhaustion and respect Telegram's message size limits.
- Restricted local `.env` file permissions to owner-only (`600`) to protect sensitive tokens.
- Added a prominent security warning to `README.md` regarding the risks of remote command execution.

### Added
- Added detailed installation instructions for `pip`, `pipx`, and `uv` to `README.md`.
- Added project descriptors (keywords, classifiers, and URLs) to `pyproject.toml` for better metadata and discoverability.
- Added `examples/tui_echo_with_log.py`, an interactive echo bot with a rich TUI and side-logging for testing the `--output-stream` feature.

### Changed
- Shifted Phase 5 of the roadmap from "TUI Mode" to "External Output Streaming" (`--output-stream`). This allows bypassing TUI complexity by tailing a clean log file instead of capturing the PTY screen.

### Fixed
- Corrected a missing f-string in `cli.py` logging.

## [v0.0.1]

### Fixed
- Ensured `Ctrl+C` triggers graceful shutdown by restructuring `try...except asyncio.CancelledError` block within `async with application:` in `cli.py`.
- Resolved `UnboundLocalError` for `shutdown_event` by moving its initialization to an earlier point in `cli.py`.
- Implemented graceful shutdown for `Ctrl+C` and `/quit` command by using `asyncio.Event` to signal shutdown and ensuring all components are properly terminated.
- Replaced `application.run_until_disconnected()` with `async with application:` and `await asyncio.Future()` for correct asynchronous Telegram bot lifecycle management in `cli.py`.
- Reverted temporary debugging changes in `cli.py` and `telegram.py` to restore intended application flow.
- Corrected `SyntaxError` in `src/gramit/telegram.py` related to an unmatched parenthesis.

### Added
- Initial and goodbye messages sent to Telegram upon gramit startup/shutdown.
- `/quit` Telegram command to gracefully terminate the orchestrated process.
- `examples/reverse_echo.py` script for interactive testing.
- Console script `gramit` for easier execution.
- `--register` mode to easily find a user's chat ID.
- Support for `GRAMIT_CHAT_ID` environment variable as an alternative to `--chat-id`.
- Main application entrypoint (`cli.py`) to integrate all components.
- `InputRouter` to handle and authorize incoming Telegram messages.
- `OutputRouter` to process and send output in line-buffered mode.
- `AsyncDebouncer` utility to batch items after a period of inactivity.
- I/O handling (`read`/`write`) to the `Orchestrator`.
- `Orchestrator` class to manage child processes in a pseudo-terminal (PTY).
- Initial project structure with `uv`, `pytest`, and core directories.
- `GEMINI.md` with project development guidelines.
- `DESIGN.md` v2.1, a robust architectural plan for the application.
- `ROADMAP.md` detailing the phased implementation plan.
- `CHANGELOG.md` to track notable changes.
- `journal/` directory for detailed daily progress logs.

### Changed
- Overhauled the initial system design to address critical security, dependency, and usability issues.