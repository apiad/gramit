import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

# Initialize Rich Console
console = Console()

# Configuration
LOG_FILE = "tui_echo.log"

def log_message(msg: str):
    """Appends a clean message to the log file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}
")
        f.flush()

def make_layout() -> Layout:
    """Creates a basic layout with a header, body, and footer."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    return layout

def main():
    # Ensure log file starts fresh for this session
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    log_message("SYSTEM: Application started.")
    
    layout = make_layout()
    layout["header"].update(Panel(Text("Gramit TUI Echo Example", justify="center", style="bold magenta"), border_style="magenta"))
    layout["footer"].update(Panel(Text("Type something and press Enter (or 'quit' to exit)", justify="center", style="dim"), border_style="cyan"))
    
    messages = []
    
    def update_body():
        msg_text = Text()
        for m in messages[-10:]:  # Show last 10 messages
            msg_text.append(f"> {m}
", style="green")
        layout["body"].update(Panel(msg_text, title="Messages", border_style="green"))

    update_body()

    with Live(layout, console=console, refresh_per_second=4, screen=True):
        while True:
            try:
                # Use standard input for interaction
                user_input = console.input("[bold yellow]Input: [/]").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "exit"]:
                    log_message("SYSTEM: User requested exit.")
                    break
                
                # Echo logic
                response = f"Echo: {user_input}"
                messages.append(user_input)
                messages.append(response)
                
                # Log the interaction (this is what gramit will tail)
                log_message(f"USER: {user_input}")
                log_message(f"BOT:  {response}")
                
                update_body()
                
            except EOFError:
                log_message("SYSTEM: EOF reached.")
                break
            except KeyboardInterrupt:
                log_message("SYSTEM: KeyboardInterrupt.")
                break

    console.print("[bold red]Exiting...[/]")
    log_message("SYSTEM: Application terminated.")

if __name__ == "__main__":
    main()
