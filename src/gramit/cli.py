import os
import asyncio
import argparse
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

from .orchestrator import Orchestrator
from .router import OutputRouter
from .telegram import InputRouter


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    print(f"Error: {context.error}")
    if update:
        print(f"Update: {update}")


async def _register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A simple handler that prints information about any message it receives."""
    if not update.message:
        return

    chat_id = update.message.chat.id
    username = update.message.from_user.username or "N/A"
    text = update.message.text or ""

    print("--- Message Received ---")
    print(f"  Chat ID: {chat_id}")
    print(f"  From:    @{username}")
    print(f"  Message: {text}")
    print("------------------------\n")
    
    await update.message.reply_text(f"Your Chat ID is: {chat_id}")


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
        default=os.getenv("GRAMIT_CHAT_ID"),
        help="The authorized Telegram chat ID. Can also be set via GRAMIT_CHAT_ID env var.",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Run in registration mode to find a chat ID.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The command to execute.",
    )
    # --line-mode will be used in a future phase
    parser.add_argument("--line-mode", action="store_true", help="Enable line mode.")

    args = parser.parse_args()
    token = os.getenv("GRAMIT_TELEGRAM_TOKEN")
    if not token:
        raise ValueError("GRAMIT_TELEGRAM_TOKEN environment variable not set.")

    # --- Registration Mode ---
    if args.register:
        print("Starting in registration mode...")
        print("Send any message to the bot to see your Chat ID.")
        application = Application.builder().token(token).build()
        application.add_handler(MessageHandler(filters.TEXT, _register_handler))
        application.add_error_handler(error_handler)
        async with application:
            await application.start()
            await application.updater.start_polling()
            # Keep it running until manually stopped
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                pass
            finally:
                await application.updater.stop()
                await application.stop()
        return

    # --- Main Gramit Logic ---
    if not args.chat_id:
        parser.error("the following arguments are required: --chat-id (or GRAMIT_CHAT_ID env var)")
    if not args.command:
        parser.error("the following arguments are required: command")

    # --- Component Setup ---
    orchestrator = Orchestrator(args.command)

    bot = Bot(token)
    sender = lambda msg: bot.send_message(chat_id=args.chat_id, text=msg)

    input_router = InputRouter(
        orchestrator=orchestrator,
        authorized_chat_ids=[int(args.chat_id)],
    )
    output_router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        mode="line",
    )

    # --- Application Setup ---
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, input_router.handle_message))
    application.add_handler(CommandHandler("quit", input_router.handle_command))
    application.add_error_handler(error_handler)

    # --- Main Execution Loop ---
    output_task = None
    try:
        async with application:
            print("CLI: Initializing Telegram application...")
            await application.start()
            print("CLI: Starting Telegram application (polling)...")
            try:
                await application.updater.start_polling()
                print("CLI: Telegram application started.")
            except Exception as e:
                print(f"CLI: Error starting Telegram polling: {e}")
                await sender(f"Error starting Telegram bot: {e}. Please check your token.")
                return

            # Send initial message
            initial_message = (
                f"Gramit started for command: `{' '.join(args.command)}`\n"
                f"Broadcasting to chat ID: `{args.chat_id}`\n"
                "Send `/quit` to terminate the process."
            )
            await sender(initial_message)

            proc_pid = await orchestrator.start()
            print(f"CLI: Started process {proc_pid} with command: {' '.join(args.command)}")
            print(f"CLI: Broadcasting to Telegram chat ID: {args.chat_id}")

            output_task = asyncio.create_task(output_router.start())
            
            # Run both tasks concurrently. If one finishes, the other should be cancelled.
            # The asyncio.Future() keeps the event loop alive for the Telegram bot.
            await asyncio.gather(output_task, asyncio.Future())

            print("CLI: Orchestrated process has terminated.")
            # Send goodbye message
            await sender("Orchestrated process has terminated. Goodbye!")

    except asyncio.CancelledError:
        print("CLI: Application cancelled (e.g., via Ctrl+C). Initiating graceful shutdown.")
        # Ensure all components are shut down
        if orchestrator.is_alive():
            print("CLI: Orchestrator process still alive, shutting down.")
            await orchestrator.shutdown()
        if output_task and not output_task.done():
            print("CLI: Output task still running, cancelling.")
            output_task.cancel()
            try:
                await output_task
            except asyncio.CancelledError:
                pass
        # Send goodbye on interrupt
        await sender("Gramit application was interrupted. Goodbye!")
    except Exception as e:
        print(f"CLI: An unexpected error occurred: {e}")
        # Send error message to Telegram
        await sender(f"Gramit encountered an error: {e}. Shutting down.")
    finally:
        print("CLI: Stopping Telegram application...")
        # The async with block handles application.stop() and application.updater.stop()
        # No need to explicitly call them here.


def run():
    """Sync entrypoint for the console script."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run()


def run():
    """Sync entrypoint for the console script."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run()