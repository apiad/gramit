import os
import asyncio
import argparse
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters

from .orchestrator import Orchestrator
from .router import OutputRouter
from .telegram import InputRouter


async def main():
    """
    Main entrypoint for the gramit application.
    """
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Gramit: Bridge a local CLI application with a remote Telegram interface."
    )
    parser.add_argument(
        "--chat-id",
        type=int,
        required=True,
        help="The authorized Telegram chat ID to interact with.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The command to execute.",
    )
    # --line-mode will be used in a future phase
    parser.add_argument("--line-mode", action="store_true", help="Enable line mode.")

    args = parser.parse_args()

    if not args.command:
        parser.error("the following arguments are required: command")

    token = os.getenv("GRAMIT_TELEGRAM_TOKEN")
    if not token:
        raise ValueError("GRAMIT_TELEGRAM_TOKEN environment variable not set.")

    # --- Component Setup ---
    orchestrator = Orchestrator(args.command)

    bot = Bot(token)
    sender = lambda msg: bot.send_message(chat_id=args.chat_id, text=msg)

    input_router = InputRouter(
        orchestrator=orchestrator,
        authorized_chat_ids=[args.chat_id],
    )
    output_router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        mode="line",
    )

    # --- Application Setup ---
    application = Application.builder().token(token).build()
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, input_router.handle_message)
    )

    # --- Main Execution Loop ---
    async with application:
        await application.initialize()
        await application.start()

        proc_pid = await orchestrator.start()
        print(f"Started process {proc_pid} with command: {' '.join(args.command)}")
        print(f"Broadcasting to Telegram chat ID: {args.chat_id}")

        output_task = asyncio.create_task(output_router.start())

        # Wait for the orchestrated process to finish
        while orchestrator.is_alive():
            await asyncio.sleep(1)

        print("Orchestrated process has terminated.")
        output_task.cancel()
        await application.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        print(f"Error: {e}")
