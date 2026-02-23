import os
import asyncio
import argparse
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
)

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
        "-o",
        "--output-stream",
        help="Path to a file to tail for output instead of PTY stdout.",
    )
    parser.add_argument(
        "--no-mirror",
        action="store_false",
        dest="mirror",
        help="Disable mirroring the orchestrated process output to the local terminal.",
    )
    parser.set_defaults(mirror=True)
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
        parser.error(
            "the following arguments are required: --chat-id (or GRAMIT_CHAT_ID env var)"
        )
    if not args.command:
        parser.error("the following arguments are required: command")

    # --- Main Execution Loop ---
    output_task = None
    shutdown_event = asyncio.Event()  # New: Event to signal shutdown

    # --- Component Setup ---
    orchestrator = Orchestrator(args.command)

    bot = Bot(token)

    def sender(msg):
        return bot.send_message(chat_id=args.chat_id, text=msg)

    input_router = InputRouter(
        orchestrator=orchestrator,
        authorized_chat_ids=[int(args.chat_id)],
        shutdown_event=shutdown_event,  # New: Pass the shutdown event
    )
    output_router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        mode="line",
        output_stream=args.output_stream,
        mirror=args.mirror,
    )

    # --- Application Setup ---
    application = Application.builder().token(token).build()
    # Route regular text to handle_message
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, input_router.handle_message)
    )
    # Route ALL commands to handle_command
    application.add_handler(
        MessageHandler(filters.COMMAND, input_router.handle_command)
    )
    application.add_error_handler(error_handler)

    try:
        async with application:
            await application.start()
            try:
                await application.updater.start_polling()
            except Exception as e:
                await sender(
                    f"Error starting Telegram bot: {e}. Please check your token."
                )
                return

            # Send initial message
            initial_message = (
                f"Gramit started for command: `{' '.join(args.command)}`\n"
                f"Broadcasting to chat ID: `{args.chat_id}`\n"
                "Send `/help` for key shortcuts or `/quit` to terminate."
            )
            await sender(initial_message)

            await orchestrator.start()
            
            # Handle window resize signals
            import signal
            loop = asyncio.get_running_loop()
            try:
                loop.add_signal_handler(signal.SIGWINCH, orchestrator.resize)
            except (NotImplementedError, AttributeError):
                # signal.SIGWINCH might not be available on all platforms
                pass

            output_task = asyncio.create_task(output_router.start())

            try:
                await asyncio.gather(output_task, shutdown_event.wait())
            except asyncio.CancelledError:
                # Ensure orchestrator and output_task are shut down
                if orchestrator.is_alive():
                    await orchestrator.shutdown()
                if output_task and not output_task.done():
                    output_task.cancel()
                    try:
                        await output_task
                    except asyncio.CancelledError:
                        pass
                # The async with application block's __aexit__ will handle Telegram app shutdown.
                await sender("Gramit application was interrupted. Goodbye!")
                raise  # Re-raise to allow async with to handle it

            await sender("Orchestrated process has terminated. Goodbye!")

    except Exception as e:  # Catch any other exceptions
        await sender(f"Gramit encountered an error: {e}. Shutting down.")
    finally:
        pass
        # The async with application's __aexit__ handles Telegram app shutdown.
        # We don't need to explicitly call application.stop() here.


def run():
    """Sync entrypoint for the console script."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run()
