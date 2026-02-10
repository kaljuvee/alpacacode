#!/usr/bin/env python3
"""
Strategy Backtester CLI - Main Entry Point
Simplified CLI for backtesting trading strategies
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from tui.strategy_cli import StrategyCLI
import asyncio


def main():
    """Main entry point for Strategy Backtester CLI."""
    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Create and run CLI
    cli = StrategyCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
