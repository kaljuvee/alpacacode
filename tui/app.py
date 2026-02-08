"""
Strategy Simulator TUI Application
Terminal UI for backtesting trading strategies
"""
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Input, Markdown, Static
from textual.binding import Binding
from typing import Optional
import os


class StatusPanel(Static):
    """Status panel showing current operation status."""
    
    def update_status(self, message: str) -> None:
        self.update(f"[bold yellow]Status:[/bold yellow] {message}")


class StrategySimulatorApp(App):
    """Full Textual TUI application for Strategy Simulator."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main_container {
        height: 1fr;
        padding: 1;
    }

    #result_view {
        height: 1fr;
        border: solid $accent;
        padding: 1;
        overflow-y: scroll;
    }

    #status_bar {
        height: 3;
        padding: 1;
        background: $surface-lighten-1;
        color: $text;
        border-top: solid $primary;
    }

    #input_container {
        height: auto;
        dock: bottom;
        padding: 1;
    }

    Input {
        border: tall $primary;
    }
    
    #intro {
        padding: 1;
        background: $surface-lighten-1;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+l", "clear_results", "Clear Results", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.current_strategy = None
        self.current_symbols = []
        self.command_history = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main_container"):
            yield Static(
                "[bold cyan]Strategy Simulator TUI[/bold cyan] | Backtest Trading Strategies\n"
                "Type 'help' for available commands",
                id="intro"
            )
            yield Markdown("", id="result_view")
        yield StatusPanel("Ready", id="status_bar")
        with Horizontal(id="input_container"):
            yield Input(placeholder="Enter command (e.g., alpaca:backtest strategy:buy-the-dip lookback:1m)", id="command_input")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app when it starts."""
        self.query_one("#command_input").focus()
        
        # Show welcome message
        welcome_msg = """# Welcome to Strategy Simulator TUI

## Quick Start Commands

### Alpaca Backtesting
```
alpaca:backtest strategy:buy-the-dip lookback:1m
alpaca:backtest strategy:momentum lookback:3m
```

### Available Strategies
- `buy-the-dip` - Buy on price dips with take-profit/stop-loss
- `momentum` - Momentum-based trading strategy

### Lookback Periods
- `1m`, `2m`, `3m`, `6m`, `1y` (months or year)

### Additional Commands
- `help` - Show this help message
- `status` - Show current configuration
- `clear` - Clear results
- `q` or `exit` - Quit application

Type a command to get started!
"""
        markdown_view = self.query_one("#result_view", Markdown)
        markdown_view.update(welcome_msg)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Process the user command."""
        from tui.command_processor import CommandProcessor
        
        command = event.value.strip()
        if not command:
            return

        # Reset input
        input_widget = self.query_one("#command_input", Input)
        status_panel = self.query_one("#status_bar", StatusPanel)
        markdown_view = self.query_one("#result_view", Markdown)
        
        input_widget.value = ""
        self.command_history.append(command)
        
        # Process command
        processor = CommandProcessor(self)
        try:
            status_panel.update_status(f"Processing: {command}")
            result = await processor.process_command(command)
            
            if result:
                markdown_view.update(result)
                status_panel.update_status("Ready")
        except Exception as e:
            error_msg = f"# Error\n\n```\n{str(e)}\n```\n\nType 'help' for available commands."
            markdown_view.update(error_msg)
            status_panel.update_status(f"Error: {str(e)}")
            self.notify(f"Error: {str(e)}", severity="error")

    def action_clear_results(self) -> None:
        """Clear the results view."""
        self.query_one("#result_view", Markdown).update("")
        self.notify("Results cleared")
