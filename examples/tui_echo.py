import os
from datetime import datetime
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import VerticalScroll

# Configuration
LOG_FILE = "tui_echo.log"

def log_message(sender: str, msg: str):
    """Appends a clean message to the log file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp} - {sender}: {msg}\n")
        f.flush()

class ChatBubble(Static):
    """A widget for a chat message bubble."""
    def __init__(self, sender: str, text: str):
        super().__init__()
        self.sender = sender
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(f"[b]{self.sender}[/b]", classes="sender")
        yield Static(self.text, classes="message")

class ChatApp(App):
    """A modern terminal chat application."""

    CSS = """
    Screen {
        background: #1a1a1a;
    }

    Header {
        background: #004466;
        color: white;
    }

    #chat-log {
        height: 1fr;
        padding: 1;
        scrollbar-gutter: stable;
    }

    ChatBubble {
        margin: 1 0;
        width: 100%;
        height: auto;
    }

    ChatBubble .sender {
        margin-bottom: 0;
        padding: 0 1;
    }

    ChatBubble .message {
        background: #333333;
        padding: 1 2;
        width: auto;
        max-width: 80%;
    }

    ChatBubble.user-message {
        align: right top;
    }

    ChatBubble.user-message .sender {
        color: #00ccff;
        text-align: right;
    }

    ChatBubble.user-message .message {
        background: #004466;
        text-align: right;
    }

    ChatBubble.bot-message {
        align: left top;
    }

    ChatBubble.bot-message .sender {
        color: #00ff99;
    }

    ChatBubble.bot-message .message {
        background: #1e332a;
    }

    Input {
        dock: bottom;
        margin: 1;
        border: solid #004466;
        background: #222222;
        color: white;
    }

    Input:focus {
        border: heavy #00ccff;
    }
    """

    def on_mount(self) -> None:
        """Called when the app starts."""
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        log_message("SYSTEM", "Application started.")
        self.query_one(Input).focus()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield VerticalScroll(id="chat-log")
        yield Input(placeholder="Type your message here and press Enter...")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_text = event.value.strip()
        if not user_text:
            return

        # Clear input field
        self.query_one(Input).value = ""

        # 1. User Message
        bubble = ChatBubble("You", user_text)
        bubble.add_class("user-message")
        chat_log = self.query_one("#chat-log")
        chat_log.mount(bubble)
        chat_log.scroll_end(animate=False)
        log_message("USER", user_text)

        if user_text.lower() in ["quit", "exit"]:
            log_message("SYSTEM", "User requested exit.")
            self.exit()
            return

        # 2. Simulate small delay for Bot response
        # In Textual, we can use call_later for a brief pause
        self.set_timer(0.4, lambda: self.bot_respond(user_text))

    def bot_respond(self, user_text: str) -> None:
        """Handles the bot's response logic."""
        response_text = f"Bot says: I received your message '{user_text}'"

        bubble = ChatBubble("Gramit Bot", response_text)
        bubble.add_class("bot-message")

        chat_log = self.query_one("#chat-log")
        chat_log.mount(bubble)
        chat_log.scroll_end(animate=False)

        log_message("BOT", response_text)

if __name__ == "__main__":
    app = ChatApp()
    app.run()
