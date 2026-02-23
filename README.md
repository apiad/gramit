# Gramit

Gramit bridges a local CLI application with a remote Telegram interface. You can run a long-running command on your machine and interact with it from anywhere using Telegram.

## Setup

1.  **Installation** (coming soon)

2.  **Get a Telegram Bot Token**
    - Talk to the [@BotFather](https://t.me/BotFather) on Telegram.
    - Create a new bot and copy the token it gives you.

3.  **Set Environment Variable**
    - Create a file named `.env` in the project root.
    - Add the following line to it:
      ```
      GRAMIT_TELEGRAM_TOKEN="YOUR_TOKEN_HERE"
      ```

4.  **Find Your Chat ID**
    - Talk to a bot like [@userinfobot](https://t.me/userinfobot) to get your numerical Telegram user ID. This will be your Chat ID.

## Usage

Run `gramit` with your desired chat ID and the command you want to execute.

```sh
uv run python -m gramit.cli --chat-id YOUR_CHAT_ID ping 8.8.8.8
```

- Replace `YOUR_CHAT_ID` with the ID you found in the setup steps.
- Any text you send to your bot on Telegram will be piped to the `stdin` of the running command.
- Any `stdout` from the command will be sent back to you as a Telegram message.
