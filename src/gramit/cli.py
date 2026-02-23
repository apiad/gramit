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
        application.add_error_handler(error_handler) # Add error handler
        async with application:
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            # Keep it running until manually stopped
            while True:
                await asyncio.sleep(3600)
        return

    # --- Main Gramit Logic ---
    if not args.chat_id:
        parser.error("the following arguments are required: --chat-id (or GRAMIT_CHAT_ID env var)")
    if not args.command:
        parser.error("the following arguments are required: command")

    # --- Component Setup ---
    # orchestrator = Orchestrator(args.command) # Temporarily commented out

    bot = Bot(token)
    sender = lambda msg: bot.send_message(chat_id=args.chat_id, text=msg)

    input_router = InputRouter(
        orchestrator=None, # Temporarily set to None
        authorized_chat_ids=[int(args.chat_id)],
    )
    # output_router = OutputRouter( # Temporarily commented out
    #     orchestrator=orchestrator,
    #     sender=sender,
    #     mode="line",
    # )

    # --- Application Setup ---
    application = Application.builder().token(token).build()
    # Catch all messages for debugging
    application.add_handler(MessageHandler(filters.ALL, input_router.handle_message))
    application.add_handler(CommandHandler("quit", input_router.handle_command))
    application.add_handler(CommandHandler("start", input_router.handle_start)) # Add /start handler
    application.add_error_handler(error_handler) # Add error handler

    # --- Main Execution Loop ---
    # output_task = None # Temporarily commented out
    # telegram_polling_task = None # Temporarily commented out
    try:
        print("CLI: Initializing Telegram application...")
        await application.initialize()
        print("CLI: Starting Telegram application (polling)...")
        try:
            await application.updater.start_polling()
            print("CLI: Telegram application started.")
        except Exception as e:
            print(f"CLI: Error starting Telegram polling: {e}")
            await sender(f"Error starting Telegram bot: {e}. Please check your token.")
            return # Exit if polling fails

        # Send initial message
        initial_message = (
            f"Gramit started for command: `{' '.join(args.command)}`\n"
            f"Broadcasting to chat ID: `{args.chat_id}`\n"
            "Send `/quit` to terminate the process."
        )
        await sender(initial_message)

        # proc_pid = await orchestrator.start() # Temporarily commented out
        # print(f"CLI: Started process {proc_pid} with command: {' '.join(args.command)}") # Temporarily commented out
        # print(f"CLI: Broadcasting to Telegram chat ID: {args.chat_id}") # Temporarily commented out

        # output_task = asyncio.create_task(output_router.start()) # Temporarily commented out
        # telegram_polling_task = asyncio.create_task(application.run_until_disconnected()) # Temporarily commented out

        # Run both tasks concurrently. If one finishes, the other should be cancelled.
        # await asyncio.gather(output_task, telegram_polling_task) # Temporarily commented out

        # Keep the Telegram bot running indefinitely for testing
        print("CLI: Telegram bot running in isolation. Send messages to test reception.")
        await asyncio.Future() # This will keep the loop running indefinitely

        # print("CLI: Orchestrated process has terminated.") # Temporarily commented out
        # Send goodbye message
        await sender("Orchestrated process has terminated. Goodbye!") # Temporarily modified message

    except asyncio.CancelledError:
        print("CLI: Application cancelled (e.g., via Ctrl+C). Initiating graceful shutdown.")
        # Ensure all components are shut down
        # if orchestrator.is_alive(): # Temporarily commented out
        #     print("CLI: Orchestrator process still alive, shutting down.") # Temporarily commented out
        #     await orchestrator.shutdown() # Temporarily commented out
        # if output_task and not output_task.done(): # Temporarily commented out
        #     print("CLI: Output task still running, cancelling.") # Temporarily commented out
        #     output_task.cancel() # Temporarily commented out
        #     try: # Temporarily commented out
        #         await output_task # Temporarily commented out
        #     except asyncio.CancelledError: # Temporarily commented out
        #         pass # Temporarily commented out
        # if telegram_polling_task and not telegram_polling_task.done(): # Temporarily commented out
        #     print("CLI: Telegram polling task still running, cancelling.") # Temporarily commented out
        #     telegram_polling_task.cancel() # Temporarily commented out
        #     try: # Temporarily commented out
        #         await telegram_polling_task # Temporarily commented out
        #     except asyncio.CancelledError: # Temporarily commented out
        #         pass # Temporarily commented out
        # Send goodbye on interrupt
        await sender("Gramit application was interrupted. Goodbye!")
    except Exception as e:
        print(f"CLI: An unexpected error occurred: {e}")
        # Send error message to Telegram
        await sender(f"Gramit encountered an error: {e}. Shutting down.")
    finally:
        print("CLI: Stopping Telegram application...")
        if application.running: # Only stop if it's actually running
            await application.stop()
        print("CLI: Telegram application stopped.")


def run():
    """Sync entrypoint for the console script."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run()