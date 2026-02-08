#!/usr/bin/env python3
"""
Strategy Simulator TUI - Main Entry Point
Terminal UI for backtesting trading strategies
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from tui.app import StrategySimulatorApp


def main():
    """Main entry point for Strategy Simulator TUI."""
    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Create and run app
    app = StrategySimulatorApp()
    app.run()


if __name__ == "__main__":
    main()
