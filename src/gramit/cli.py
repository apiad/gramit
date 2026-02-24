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
    await update.message.reply_text(
        f"Your Chat ID is: `{chat_id}`", parse_mode="Markdown"
    )


# Global reference for the output router to allow cleanup in case of KeyboardInterrupt
_current_output_router = None

async def main():
    """
    Main entrypoint for the gramit application.
    """
    global _current_output_router
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
        "-e",
        "--enter",
        dest="enter",
        action="store_true",
        help="Inject an /enter (\\r) after each Telegram message. Enabled by default.",
    )
    parser.add_argument(
        "--no-enter",
        action="store_false",
        dest="enter",
        help="Disable injecting an /enter after each Telegram message.",
    )
    parser.set_defaults(enter=True)
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
    shutdown_event = asyncio.Event()

    # --- Component Setup ---
    orchestrator = Orchestrator(args.command)

    bot = Bot(token)

    async def sender(msg):
        return await bot.send_message(chat_id=args.chat_id, text=msg, parse_mode="Markdown")

    input_router = InputRouter(
        orchestrator=orchestrator,
        authorized_chat_ids=[int(args.chat_id)],
        shutdown_event=shutdown_event,
        inject_enter=args.enter,
    )
    output_router = OutputRouter(
        orchestrator=orchestrator,
        sender=sender,
        mode="line",
        output_stream=args.output_stream,
        mirror=args.mirror,
    )
    _current_output_router = output_router

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
                    f"Error starting Telegram bot: `{e}`. Please check your token."
                )
                return

            # Send initial message
            initial_message = (
                f"*Gramit started for command:* `{' '.join(args.command)}`\n"
                f"*Broadcasting to chat ID:* `{args.chat_id}`\n\n"
                "Send `/help` for key shortcuts or `/quit` to terminate."
            )
            await sender(initial_message)

            await orchestrator.start()

            # Handle window resize and shutdown signals
            import signal
            loop = asyncio.get_running_loop()

            def handle_shutdown():
                shutdown_event.set()

            try:
                loop.add_signal_handler(signal.SIGWINCH, orchestrator.resize)
                # Register SIGINT and SIGTERM to set the shutdown_event
                # This ensures we enter our cleanup logic gracefully
                loop.add_signal_handler(signal.SIGINT, handle_shutdown)
                loop.add_signal_handler(signal.SIGTERM, handle_shutdown)
            except (NotImplementedError, AttributeError):
                pass

            try:
                # Prepare terminal for mirroring BEFORE starting the task
                output_router.prepare_terminal()

                # Start the output router task
                output_task = asyncio.create_task(output_router.start())

                # Wait for either the output task to finish or the shutdown event
                done, pending = await asyncio.wait(
                    [output_task, asyncio.create_task(shutdown_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED
                )
            finally:
                # Security: Remove signal handlers once we start shutting down
                try:
                    loop.remove_signal_handler(signal.SIGINT)
                    loop.remove_signal_handler(signal.SIGTERM)
                except Exception:
                    pass

                # Ensure terminal is restored regardless of how we exited
                output_router.restore_terminal()

                # Ensure orchestrator and output_task are shut down gracefully
                if orchestrator.is_alive():
                    await orchestrator.shutdown()

                if output_task and not output_task.done():
                    output_task.cancel()
                    try:
                        await output_task
                    except (asyncio.CancelledError, Exception):
                        pass

                # Check if we should send a goodbye message
                if shutdown_event.is_set():
                    await sender("Gramit application was interrupted. Goodbye!")
                else:
                    await sender("Orchestrated process has terminated. Goodbye!")

    except (KeyboardInterrupt, asyncio.CancelledError):
        # Handle cases where asyncio.run might cancel the main task
        pass
    except Exception as e:  # Catch any other exceptions
        try:
            await sender(f"Gramit encountered an error: `{e}`. Shutting down.")
        except Exception:
            print(f"Gramit encountered a fatal error: {e}")
    finally:
        pass
        # The async with application's __aexit__ handles Telegram app shutdown.
        # We don't need to explicitly call application.stop() here.


def run():
    import signal
    import sys

    def signal_handler(sig, frame):
        # Immediate terminal restoration on signal
        if _current_output_router:
            _current_output_router.restore_terminal()
        # After restoration, perform default behavior or exit
        sys.exit(1)

    # Register basic signal handlers for sync cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        if isinstance(e, ValueError):
            print(f"Error: {e}")
    finally:
        # Final safety net for terminal restoration
        if _current_output_router:
            _current_output_router.restore_terminal()
