# Gramit: Architectural & System Design Document (v3.0)

## 1. System Overview & Design Principles

Gramit is a secure, self-contained Python orchestrator that bridges a local, command-line application with a remote Telegram interface. It allows a single, authorized user to control and monitor any CLI process from their Telegram chat.

This design adheres to the following principles:

*   **Security First:** The system is locked down by default. It requires explicit user authorization and uses secure methods for handling credentials.
*   **Zero External Dependencies:** The application is a pure Python tool and does not require external binaries like `tmux`. This enhances portability and reduces complexity.
*   **Remote-First Interaction:** The primary interface is Telegram. Simultaneous local terminal interaction is not supported, which eliminates input race conditions and simplifies the design.
*   **External Output Streaming:** For complex applications, Gramit can "tail" a clean log file instead of capturing raw terminal output, providing a robust way to bridge interactive TUI apps.

## 2. Core Architecture

Gramit is built on `asyncio`. When launched, it starts a main orchestrator that runs the target command in a pseudo-terminal (PTY) and manages three core asynchronous components.

![Gramit Architecture Diagram](https://i.imgur.com/9A7SO88.png)

### 2.1. The PTY Orchestrator
This component manages the child process lifecycle.

*   **Initialization:** On startup, the orchestrator uses `os.forkpty()` to create a new child process running inside a pseudo-terminal. This correctly allocates a PTY, ensuring that interactive applications behave as expected.
*   **Lifecycle Management:** The orchestrator owns the child process and the master file descriptor for the PTY. It is responsible for gracefully shutting down all components when the child process exits.

### 2.2. The Input Router (Telegram → PTY)
This component handles incoming commands from Telegram.

*   **Authorization:** It uses the `python-telegram-bot` library to listen for messages. It will **only** process messages from a single, pre-authorized `chat_id`. All other messages are discarded.
*   **Injection:** Authorized messages are written directly to the master PTY file descriptor, which passes them to the `stdin` of the running child process.

### 2.3. The Output Router (PTY/File → Telegram)
This component captures, processes, and transmits output from the application back to the user. It operates in one of two modes.

#### 2.3.1. Standard Mode (PTY-based)
This is the default mode for line-based applications.

1.  **PTY Capture:** The raw output from the PTY master descriptor is decoded (UTF-8 with replacement for errors).
2.  **Line Buffering:** Output is buffered until a newline is reached or the buffer exceeds a size limit.
3.  **Debounced Flush:** An asynchronous debouncer collects lines and flushes them after a short period of inactivity (e.g., 0.5s), ensuring that rapid bursts of output are sent as a single Telegram message.
4.  **Message Trimming:** If a flushed message exceeds Telegram's 4096-character limit, it is automatically trimmed in the middle with a warning to stay within API bounds.

#### 2.3.2. Output Stream Mode (`--output-stream <FILE>`)
This mode is designed for complex TUI applications that can write a clean interaction log to an external file.

1.  **File Tailing:** A `FileTailer` component asynchronously watches the specified file for new appends.
2.  **PTY Bypass:** The `OutputRouter` ignores the child process's `stdout` in the PTY and instead uses the data from the `FileTailer`.
3.  **Unified Processing:** The file-based data is passed through the same debouncing and trimming pipeline as standard mode, ensuring consistent message delivery to Telegram.

## 3. Security Model

### 3.1. Credential Management
*   **Environment Variables:** Sensitive tokens must be provided via `GRAMIT_TELEGRAM_TOKEN`.
*   **`.env` Support:** The application automatically loads variables from a local `.env` file.
*   **File Permissions:** Local configuration files like `.env` should be restricted to owner-only access (`chmod 600`).

### 3.2. Access Control
*   **Chat ID Locking:** The bot only responds to the specific `chat_id` provided via `--chat-id` or `GRAMIT_CHAT_ID`.
*   **Registration Mode:** A built-in `--register` flag helps users identify their `chat_id` in a secure, temporary session.

## 4. Summary of Improvements (v3.0)

| Feature | Description |
| :--- | :--- |
| **Output Streaming** | Bypasses PTY scraping complexity by tailing a clean, application-generated log file. |
| **Robust Debouncing** | Prevents Telegram API flooding and memory exhaustion with configurable flush intervals and buffer limits. |
| **PTY Orchestration** | Uses native `os.forkpty()` for zero-dependency terminal management. |
| **Security Enforcements** | Mandatory Chat ID authorization and secure token handling. |
