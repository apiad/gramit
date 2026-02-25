import os
import asyncio
import argparse
import logging
import signal
import sys
from typing import Optional

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
from .terminal import RESTORE_TERMINAL_SEQ
from .utils import logger


class GramitCLI:
    """
    Manages the Gramit Command Line Interface and application lifecycle.
    """

    def __init__(self):
        self.args: Optional[argparse.Namespace] = None
        self.orchestrator: Optional[Orchestrator] = None
        self.output_router: Optional[OutputRouter] = None
        self.shutdown_event = asyncio.Event()
        self.application: Optional[Application] = None
        self.token: Optional[str] = None

    def get_parser(self) -> argparse.ArgumentParser:
        """
        Returns the argument parser for gramit.
        """
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
            "--e",
            "--enter",
            dest="enter",
            action="store_true",
            help="Inject an /enter (\\r) after each Telegram message with a minimum delay (200ms).",
        )
        parser.add_argument(
            "--no-enter",
            action="store_false",
            dest="enter",
            help="Disable injecting an /enter after each Telegram message.",
        )
        parser.set_defaults(enter=False)
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Enable verbose logging.",
        )
        parser.add_argument(
            "--log-file",
            default="gramit.log",
            help="Path to the log file. Defaults to 'gramit.log'.",
        )
        parser.add_argument(
            "command",
            nargs=argparse.REMAINDER,
            help="The command to execute.",
        )
        parser.add_argument("--line-mode", action="store_true", help="Enable line mode.")
        return parser

    def setup_logging(self):
        """
        Configures logging based on the provided arguments.
        """
        logging.basicConfig(
            level=logging.DEBUG if self.args.verbose else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=self.args.log_file,
            filemode="a",
        )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        logger.error(f"Telegram error: {context.error}")
        if update:
            logger.debug(f"Update that caused the error: {update}")

    async def _register_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """A simple handler that prints information about any message it receives."""
        if not update.message:
            return

        chat_id = update.message.chat.id
        await update.message.reply_text(
            f"Your Chat ID is: `{chat_id}`", parse_mode="Markdown"
        )

    async def run_registration(self):
        """
        Runs the bot in registration mode to help users find their Chat ID.
        """
        print("Starting in registration mode...")
        print("Send any message to the bot to see your Chat ID.")
        self.application = Application.builder().token(self.token).build()
        self.application.add_handler(MessageHandler(filters.TEXT, self._register_handler))
        self.application.add_error_handler(self.error_handler)
        
        async with self.application:
            await self.application.start()
            await self.application.updater.start_polling()
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                pass
            finally:
                await self.application.updater.stop()
                await self.application.stop()

    async def sender(self, bot: Bot, msg: str):
        """
        Helper method to send a message to the authorized chat ID.
        """
        try:
            return await bot.send_message(
                chat_id=self.args.chat_id, text=msg, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def _setup_signal_handlers(self):
        """
        Registers signal handlers for graceful shutdown and window resizing.
        """
        loop = asyncio.get_running_loop()

        def handle_shutdown():
            self.shutdown_event.set()

        try:
            loop.add_signal_handler(signal.SIGWINCH, self.orchestrator.resize)
            loop.add_signal_handler(signal.SIGINT, handle_shutdown)
            loop.add_signal_handler(signal.SIGTERM, handle_shutdown)
        except (NotImplementedError, AttributeError):
            pass

    def _cleanup_signal_handlers(self):
        """
        Removes previously registered signal handlers.
        """
        loop = asyncio.get_running_loop()
        try:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        except Exception:
            pass

    async def main(self):
        """
        Primary execution logic for the Gramit application.
        """
        load_dotenv()
        parser = self.get_parser()
        self.args = parser.parse_args()
        
        self.setup_logging()
        
        self.token = os.getenv("GRAMIT_TELEGRAM_TOKEN")
        if not self.token:
            print("Error: GRAMIT_TELEGRAM_TOKEN environment variable not set.")
            return

        if self.args.register:
            await self.run_registration()
            return

        if not self.args.chat_id:
            parser.error("the following arguments are required: --chat-id (or GRAMIT_CHAT_ID env var)")
        if not self.args.command:
            parser.error("the following arguments are required: command")

        self.orchestrator = Orchestrator(self.args.command)
        bot = Bot(self.token)

        async def bot_sender(msg):
            return await self.sender(bot, msg)

        input_router = InputRouter(
            orchestrator=self.orchestrator,
            authorized_chat_ids=[int(self.args.chat_id)],
            shutdown_event=self.shutdown_event,
            inject_enter=self.args.enter,
        )
        self.output_router = OutputRouter(
            orchestrator=self.orchestrator,
            sender=bot_sender,
            mode="line",
            output_stream=self.args.output_stream,
            mirror=self.args.mirror,
        )

        self.application = Application.builder().token(self.token).build()
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, input_router.handle_message)
        )
        self.application.add_handler(
            MessageHandler(filters.COMMAND, input_router.handle_command)
        )
        self.application.add_error_handler(self.error_handler)

        output_task = None

        try:
            async with self.application:
                await self.application.start()
                try:
                    await self.application.updater.start_polling()
                except Exception as e:
                    await bot_sender(f"Error starting Telegram bot: `{e}`. Please check your token.")
                    return

                await bot_sender(
                    f"*Gramit started for command:* `{' '.join(self.args.command)}`\n"
                    f"*Broadcasting to chat ID:* `{self.args.chat_id}`\n\n"
                    "Send `/help` for key shortcuts or `/quit` to terminate."
                )

                await self.orchestrator.start()
                self._setup_signal_handlers()

                try:
                    self.output_router.prepare_terminal()
                    output_task = asyncio.create_task(self.output_router.start())
                    
                    await asyncio.wait(
                        [output_task, asyncio.create_task(self.shutdown_event.wait())],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                finally:
                    self._cleanup_signal_handlers()

                    if self.orchestrator.is_alive():
                        await self.orchestrator.shutdown()

                    self.output_router.restore_terminal()

                    if output_task and not output_task.done():
                        output_task.cancel()
                        try:
                            await output_task
                        except (asyncio.CancelledError, Exception):
                            pass

                    if self.shutdown_event.is_set():
                        await bot_sender("Gramit application was interrupted. Goodbye!")
                    else:
                        await bot_sender("Orchestrated process has terminated. Goodbye!")

        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.error(f"Gramit encountered an unhandled exception: {e}")
            try:
                await bot_sender(f"Gramit encountered an error: `{e}`. Shutting down.")
            except Exception:
                pass


# Global singleton for signal handling
_cli_instance: Optional[GramitCLI] = None

def run():
    """
    Synchronous entrypoint that handles initial setup and signal registration.
    """
    global _cli_instance
    _cli_instance = GramitCLI()

    def signal_handler(sig, frame):
        if _cli_instance.orchestrator and _cli_instance.orchestrator.is_alive():
            try:
                if _cli_instance.orchestrator._pid:
                    os.kill(_cli_instance.orchestrator._pid, 9)
            except Exception:
                pass

        if _cli_instance.output_router:
            _cli_instance.output_router.restore_terminal()
        else:
            try:
                os.write(sys.stdout.fileno(), RESTORE_TERMINAL_SEQ)
            except Exception:
                pass
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(_cli_instance.main())
    except (KeyboardInterrupt, ValueError) as e:
        if isinstance(e, ValueError):
            print(f"Error: {e}")
    finally:
        if _cli_instance.output_router:
            _cli_instance.output_router.restore_terminal()
