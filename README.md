# Gramit

Gramit bridges a local CLI application with a remote Telegram interface. You can run a long-running command on your machine and interact with it from anywhere using Telegram.

## Setup

1.  **Installation** (coming soon)

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
    - Once you have your ID, you can stop the command (`Ctrl+C`).

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
