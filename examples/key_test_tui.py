import os
from datetime import datetime
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label
from textual.containers import VerticalScroll

LOG_FILE = "key_test.log"

def log_key(key_info: str):
    """Logs key information to a file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        f.write(f"{timestamp} - {key_info}\n")
        f.flush()

class KeyTestApp(App):
    """An app to test and display key presses and modifiers."""
    
    CSS = """
    Screen {
        background: #000000;
        align: center middle;
    }
    
    #container {
        width: 80%;
        height: 80%;
        border: double #00ff00;
        background: #111111;
        padding: 1;
    }

    .title {
        text-align: center;
        width: 100%;
        color: #00ff00;
        text-style: bold;
        margin-bottom: 1;
    }

    #last-key {
        background: #222222;
        color: #ffff00;
        padding: 1 2;
        border: solid #ffff00;
        text-align: center;
        text-style: bold;
        height: 3;
        margin-bottom: 1;
    }

    #history {
        height: 1fr;
        border: solid #333333;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        log_key("SYSTEM: Key Test App Started")

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="container"):
            yield Label("PRESS ANY KEY / COMBINATION", classes="title")
            yield Static("Waiting for input...", id="last-key")
            yield Static("", id="history")
        yield Footer()
        # Bind common keys to show up in footer
        self.bind("ctrl+q", "exit", description="Quit")
        self.bind("up", "dummy", description="Up")
        self.bind("down", "dummy", description="Down")
        self.bind("home", "dummy", description="Home")
        self.bind("end", "dummy", description="End")
        self.bind("f1", "dummy", description="F1")
        self.bind("pageup", "dummy", description="PgUp")
        self.bind("pagedown", "dummy", description="PgDn")
        self.bind("insert", "dummy", description="Ins")

    def action_dummy(self) -> None:
        """Dummy action for footer visibility."""
        pass

    def on_key(self, event) -> None:
        # Format the key info
        key_name = event.key
        char = event.character or "N/A"
        
        info = f"Key: {key_name} | Char: {repr(char)}"
        
        # Update UI
        self.query_one("#last-key").update(info)
        
        history_widget = self.query_one("#history")
        # Get current text, ignoring the widget's own container stuff if possible,
        # but for this simple example we can just maintain a list.
        if not hasattr(self, "_history_list"):
            self._history_list = []
        
        self._history_list.insert(0, info)
        self._history_list = self._history_list[:15]
        
        history_widget.update("\n".join(self._history_list))
        
        # Log for gramit to tail
        log_key(info)

        if key_name == "ctrl+q":
            log_key("SYSTEM: Exit requested via Ctrl+Q")
            self.exit()

if __name__ == "__main__":
    app = KeyTestApp()
    app.run()
