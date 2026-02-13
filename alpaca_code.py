#!/usr/bin/env python3
"""
AlpacaCode CLI - Main Entry Point
Launches the Rich-based interactive CLI for backtesting, paper trading,
and monitoring the multi-agent trading system.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


def main():
    """Main entry point for AlpacaCode CLI."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    from tui.strategy_cli import StrategyCLI
    import asyncio
    cli = StrategyCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
