# Gramit: The Ultimate Telegram-to-Terminal Connector

[![Run Tests](https://github.com/apiad/gramit/actions/workflows/tests.yaml/badge.svg)](https://github.com/apiad/gramit/actions/workflows/tests.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)

Gramit is the most beautiful, robust, and secure way to bridge your local CLI applications with a remote Telegram interface. It allows you to run any command on your machine—from simple scripts to complex TUIs—and interact with it from anywhere in the world.
<!-- Hook Testing v3 -->

> [!CAUTION]
> **SECURITY WARNING: REMOTE ACCESS RISK**
>
> Gramit provides a bridge between your local machine and a remote Telegram interface. **This allows remote command execution.**
>
> If you run a shell (like `/bin/bash` or `cmd.exe`) or any interactive tool through Gramit, anyone with access to your Telegram bot (and whose Chat ID is authorized) has **full control over your machine**.
>
> **USE ONLY IF YOU ARE HIGHLY SECURITY-AWARE.**
> - Never share your `GRAMIT_TELEGRAM_TOKEN`.
> - Ensure your `GRAMIT_CHAT_ID` is correctly configured to *your* ID only.
> - Be extremely cautious when bridging shells or administrative tools.

---

## 🌟 Key Features

### 🚀 Dual Output Modes

Gramit offers two powerful ways to bridge your terminal output to Telegram:

1.  **Standard Mode (IO):** Directly captures the `stdout` of your process via a Pseudo-Terminal (PTY). Perfect for line-based apps and scripts. Gramit intelligently aggregates and debounces output to ensure you don't get spammed with dozens of tiny messages.
2.  **External Stream Mode (`-o` / `--output-stream`):** For complex TUI applications where raw terminal output is "noisy" (filled with borders, colors, and ANSI codes), you can instruct Gramit to "tail" a clean side-log file instead.

### ⌨️ Key Shortcuts & Modifiers

Interact with TUIs effortlessly using Telegram commands (use spaces between modifiers and keys):

-   **Special Keys:** `/enter`, `/esc`, `/t` (Tab), `/b` (Backspace), `/d` (Delete).
-   **Arrow Keys:** `/up`, `/down`, `/left`, `/right`.
-   **Modifiers:**
    -   `/c <key>` for Control (e.g., `/c a` for `Ctrl+A`).
    -   `/a <key>` for Alt/Meta (e.g., `/a x` for `Alt+X`).
    -   `/s <key>` for Shift.
-   **Combinations:** `/c /s a` for `Ctrl+Shift+A`, `/a /c /up` for `Alt+Ctrl+Up`, etc.

### 🖥️ Native Terminal Experience

Gramit isn't just a blind pipe; it respects your terminal:

-   **Terminal Size Inheritance:** Child processes automatically inherit the size of your host terminal on startup.
-   **Dynamic Resizing:** Resize your local terminal window, and Gramit propagates the change to the child process instantly (`SIGWINCH` support).
-   **Local Mirroring:** See the TUI running locally in your terminal while you interact with it remotely via Telegram.
-   **Robust Cleanup:** When you exit, Gramit performs a full terminal restoration—clearing the screen, homing the cursor, disabling mouse tracking, and exiting alternate screen buffers. No more "broken" terminals!

### 🔒 Built-in Security

-   **Locked-down by Default:** Only messages from your specific `chat_id` are processed.
-   **Credential Safety:** Tokens are handled via environment variables or secured `.env` files.
-   **Rate Limiting:** Protects your bot and machine from memory exhaustion and API flooding.

---

## 💡 Pro Use Case: Gemini CLI

Interactive AI CLIs are the perfect companions for Gramit. Here is how to set up **Gemini CLI** for an optimal remote experience.

```sh
gramit -o gemini.log gemini "In this section
log all intermediate thoughts and final responses
to gemini.log; acknowledge, log, and wait for my command"
```

You will see the full, beautiful TUI locally if you are at your desk. When you're away, you send prompts via Telegram, and Gramit tails the clean `gemini.log` to send the AI's responses back to you.

For a more persistent solution, consider adding that instruction to your `GEMINI.md` or `AGENT.md`.

---

## 🛠️ Setup

1.  **Installation**

    Install Gramit using your favorite Python package manager:

    **Using `pipx` (Recommended for CLI tools):**
    ```sh
    pipx install gramit
    ```

    **Using `uv`:**
    ```sh
    # Run without installing
    uvx gramit --help

    # Or install as a tool
    uv tool install gramit
    ```

2.  **Get a Telegram Bot Token**
    - Talk to the [@BotFather](https://t.me/BotFather) on Telegram.
    - Create a new bot and copy the token.

3.  **Set Environment Variables**
    - Create a file named `.env` in your project root or your home directory.
    - Add your credentials (and secure the file: `chmod 600 .env`):
      ```bash
      GRAMIT_TELEGRAM_TOKEN="YOUR_TELEGRAM_TOKEN"
      GRAMIT_CHAT_ID="YOUR_CHAT_ID"
      ```

4.  **Find Your Chat ID**
    If you don't know your ID, run:
    ```sh
    gramit --register
    ```
    Send any message to your bot, and it will reply with your ID.

---

## 📖 Usage Examples

**Simple Command:**
```sh
gramit ping 8.8.8.8
```

**Interactive TUI with Side-Log:**
```sh
# Start our built-in example chat app
gramit -o tui_echo.log python examples/tui_echo_with_log.py
```

---

## 🐧 Platform Support & Contributions

Gramit is **currently only tested on Linux (bash)**.

Because it relies on native PTY features (`os.forkpty`, `termios`, `fcntl`), behavior on macOS or Windows (WSL) may vary.

**Contributions are highly welcomed!** If you've tested Gramit on other OSes or terminals and found bugs (or fixes), please open an issue or a PR.

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.
