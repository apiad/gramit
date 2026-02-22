# Gramit: Architectural & System Design Document (v2.1)

## 1. System Overview & Design Principles

Gramit is a secure, self-contained Python orchestrator that bridges a local, command-line application with a remote Telegram interface. It allows a single, authorized user to control and monitor any CLI process from their Telegram chat.

This design adheres to the following principles:

*   **Security First:** The system is locked down by default. It requires explicit user authorization and uses secure methods for handling credentials.
*   **Zero External Dependencies:** The application is a pure Python tool and does not require external binaries like `tmux`. This enhances portability and reduces complexity.
*   **Remote-First Interaction:** The primary interface is Telegram. Simultaneous local terminal interaction is not supported, which eliminates input race conditions and simplifies the design.
*   **Intelligent TUI Parsing:** It is designed to extract meaningful text from Terminal User Interfaces (TUIs), filtering out UI "chrome" like borders and control panels.

## 2. Core Architecture

Gramit is built on `asyncio`. When launched, it starts a main orchestrator that runs the target command in a pseudo-terminal (PTY) and manages three core asynchronous components.

![Gramit Architecture Diagram](https://i.imgur.com/9A7SO88.png)

### 2.1. The PTY Orchestrator
This component replaces the `tmux` dependency.

*   **Initialization:** On startup, the orchestrator uses `os.forkpty()` to create a new child process running inside a pseudo-terminal. This correctly allocates a PTY, ensuring that interactive applications (including TUIs) behave as expected.
*   **Lifecycle Management:** The orchestrator owns the child process and the master file descriptor for the PTY. It is responsible for gracefully shutting down all components when the child process exits.

### 2.2. The Input Router (Telegram → PTY)
This component handles incoming commands from Telegram.

*   **Authorization:** It uses a Telegram bot library (e.g., `python-telegram-bot`) to listen for messages. It will **only** process messages from a single, pre-authorized `chat_id` provided at startup. All other messages are discarded.
*   **Injection:** When an authorized message is received, its text content is written directly to the master PTY file descriptor, which passes it to the `stdin` of the running child process.

### 2.3. The Output Router (PTY → Telegram)
This component intelligently captures, processes, and transmits output from the application back to the user. It operates in one of two modes.

#### 2.3.1. TUI Mode (Default)
This mode is designed for interactive applications like `htop`, `vim`, or other curses-based programs.

1.  **Virtual Screen:** The raw byte stream from the master PTY (which includes ANSI escape codes) is fed into an in-memory terminal emulator powered by the `pyte` library.
2.  **Stateful Rendering:** The `pyte` screen object processes the escape codes and maintains a complete, 2D grid representing the terminal's current visual state.
3.  **Snapshotting:** A debounced `asyncio` task runs at a configurable interval (e.g., every 2 seconds). In each interval, it dumps the current text content of the `pyte` screen.
4.  **Heuristic Filtering (Content Extraction):** Before transmission, the raw text snapshot is passed through a filtering pipeline to remove common TUI "chrome." This is a best-effort attempt to extract semantic content and includes:
    *   Removing lines that primarily consist of box-drawing characters (e.g., `│`, `─`, `┌`).
    *   Stripping common control and menu indicators (e.g., lines containing patterns like "F1 Help", "F10 Quit").
    *   Trimming leading/trailing whitespace from each line and removing empty lines from the top and bottom of the snapshot.
5.  **Transmission:** The **cleaned** text snapshot is wrapped in a Telegram markdown code block and sent using `editMessageText` to update a single, persistent "screen" message. If the snapshot exceeds Telegram's 4096-character limit, it is truncated with a warning.

#### 2.3.2. Line Mode (`--line-mode`)
This mode is for simple, non-interactive applications that produce a stream of log-like output.

1.  **Line Buffering:** The raw output from the PTY is decoded and buffered line by line.
2.  **Debounced Flush:** The debounced task flushes this buffer of lines.
3.  **Transmission:** The collected lines are joined and sent as one or more *new messages* using `sendMessage`. The router automatically handles splitting content across multiple messages if it exceeds the character limit.

## 3. Security Model

The security of the system is paramount and is addressed through two key mechanisms.

### 3.1. Credential Management
The Telegram Bot Token is treated as a sensitive secret.

*   **Environment Variable:** The token **must** be provided via an environment variable (`GRAMIT_TELEGRAM_TOKEN`).
*   **`.env` Support:** For ease of local development, the application will automatically load this variable from a `.env` file in the project root if it exists (using `python-dotenv`).
*   The insecure `-t` command-line argument has been removed.

### 3.2. Access Control
Access to the bot is strictly controlled.

*   **Required `chat_id`:** The application requires a `--chat-id <ID>` argument on startup. This locks the bot to a specific user or group.
*   **Helper Utility:** A small utility script will be provided (`gramit-get-chat-id`) to help users easily find their `chat_id`.

## 4. Summary of Countermeasures

This revised design directly addresses the challenges of the initial proposal:

| Issue | Countermeasure |
| :--- | :--- |
| **TUI Incompatibility** | Replaced `tail -f` approach with a `pyte`-based virtual screen and added a heuristic filtering layer to extract meaningful content. |
| **`tmux` Dependency** | Eliminated `tmux` entirely by using Python's native `os.forkpty()` to manage the pseudo-terminal directly. |
| **Input Race Conditions** | Removed the "local attach" feature. By making Telegram the sole source of input, race conditions are impossible. |
| **Output Limits** | Implemented two distinct output modes (TUI and Line) with intelligent handling of message edits, new messages, and character limits. |
| **Security Flaws** | Enforced secure token handling via environment variables and mandated `chat_id` authorization to lock down the bot. |