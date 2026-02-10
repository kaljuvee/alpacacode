#!/usr/bin/env python3
"""
Simplified CLI interface for Strategy Backtester.
Uses Rich for formatting instead of complex TUI framework.
"""
import asyncio
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


class StrategyCLI:
    """Simplified CLI application for Strategy Backtester."""

    def __init__(self):
        self.console = Console()
        self.command_history = []
        self.current_strategy = None
        self.current_symbols = []

    async def process_command(self, command: str):
        """Process a user command and display results."""
        from tui.command_processor import CommandProcessor
        
        processor = CommandProcessor(self)
        
        try:
            result = await processor.process_command(command)
            
            if result:
                # Display result as markdown
                self.console.print("\n")
                self.console.print(Markdown(result))
                self.console.print("\n")
        except Exception as e:
            self.console.print(f"\n[red]Error:[/red] {str(e)}\n")
            import traceback
            traceback.print_exc()

    async def run(self):
        """Run the CLI interactive loop."""
        # Display welcome banner
        welcome = Panel.fit(
            "[bold cyan]Strategy Backtester CLI[/bold cyan]\n"
            "Backtest trading strategies with historical data\n\n"
            "Type [yellow]'help'[/yellow] for commands or [yellow]'q'[/yellow] to quit",
            border_style="cyan"
        )
        self.console.print("\n")
        self.console.print(welcome)
        self.console.print("\n")

        # Show quick start
        quick_start = """## Quick Start

Try these commands:
```
alpaca:backtest strategy:buy-the-dip lookback:1m
alpaca:backtest strategy:momentum lookback:3m symbols:AAPL,TSLA
help
status
```
"""
        self.console.print(Markdown(quick_start))
        self.console.print("")

        while True:
            try:
                # Get user input
                user_input = self.console.input("[bold green]>[/bold green] ").strip()

                if not user_input:
                    continue

                # Handle exit commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self.console.print("\n[yellow]Goodbye![/yellow]\n")
                    break

                # Store in history
                self.command_history.append(user_input)

                # Process command
                await self.process_command(user_input)

            except KeyboardInterrupt:
                self.console.print("\n\n[yellow]Goodbye![/yellow]\n")
                break
            except EOFError:
                self.console.print("\n\n[yellow]Goodbye![/yellow]\n")
                break
            except Exception as e:
                self.console.print(f"\n[red]Unexpected error:[/red] {str(e)}\n")
                import traceback
                traceback.print_exc()


def main():
    """Main entry point for Strategy CLI."""
    cli = StrategyCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
