# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.0.1]

### Fixed
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