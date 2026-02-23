# Gramit

[![Run Tests](https://github.com/apiad/gramit/actions/workflows/tests.yaml/badge.svg)](https://github.com/apiad/gramit/actions/workflows/tests.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)

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

Gramit bridges a local CLI application with a remote Telegram interface. It allows you to run any long-running command on your machine and interact with it from anywhere using Telegram. While designed to be generic for any CLI, it's particularly useful for interactive AI CLIs like **Gemini CLI**, **Claude Code**, or similar tools where you want to maintain a persistent session and interact remotely.

## How it Works

Gramit acts as a conduit between your local command-line application and your Telegram bot.
-   **Input Redirection:** Any message you send to your Telegram bot is piped directly to the `stdin` of the running local command.
-   **Output Capture:** All `stdout` from your local command is captured and sent back to you as a Telegram message.
-   **Session Management:** It maintains a persistent session, allowing for continuous interaction with your CLI application.

## Setup

1.  **Installation**

    You can install Gramit using your favorite Python package manager:

    **Using `pip`:**
    ```sh
    pip install gramit
    ```

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
    - Create a new bot and copy the token it gives you.

3.  **Set Environment Variables**
    - Create a file named `.env` in the project root.
    - Add the following line to it, replacing `YOUR_TOKEN_HERE` with the token you just got:
      ```
      GRAMIT_TELEGRAM_TOKEN="YOUR_TOKEN_HERE"
      ```
    - You can also optionally add your Chat ID to this file (see step 4):
      ```
      GRAMIT_CHAT_ID="YOUR_CHAT_ID_HERE"
      ```

4.  **Find Your Chat ID**
    - The easiest way to find your chat ID is to use Gramit's built-in registration mode. Run the following command:
      ```sh
      gramit --register
      ```
    - Now, send any message to your bot on Telegram. Gramit will print your Chat ID to the console and also reply with it.
    - Once you have your ID, you can stop the command (`Ctrl_C`).

## Usage

Run `gramit` with your command. If you have not set `GRAMIT_CHAT_ID` in your `.env` file, you must also provide the `--chat-id` argument.

**Basic Example:**
```sh
# If GRAMIT_CHAT_ID is set in .env
gramit ping 8.8.8.8

# If GRAMIT_CHAT_ID is NOT set
gramit --chat-id YOUR_CHAT_ID ping 8.8.8.8
```

- Any text you send to your bot on Telegram will be piped to the `stdin` of the running command.
- Any `stdout` from the command will be sent back to you as a Telegram message.

**Interactive Example (Reverse Echo):**
```sh
gramit python examples/reverse_echo.py
```
Then, send messages to your bot on Telegram. It will echo them back in reverse.

**Features:**
- Upon starting, Gramit sends an initial message to Telegram indicating the command being run.
- When the orchestrated process ends, a "goodbye" message is sent to Telegram.
- Send `/quit` to your bot to gracefully terminate the running command from Telegram.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributions

Contributions are welcome! If you have suggestions for improvements, new features, or bug fixes, please open an issue or submit a pull request.