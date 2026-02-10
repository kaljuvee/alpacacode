"""
Command Processor for Strategy Simulator TUI
Handles command parsing and execution
"""
import sys
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from rich.console import Console
from rich.table import Table
import pandas as pd


class CommandProcessor:
    """Processes commands for the Strategy Simulator TUI."""

    def __init__(self, app_instance):
        self.app = app_instance
        self.console = Console()
        
        # Default parameters
        self.default_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
        self.default_capital = 10000
        self.default_position_size = 10  # percentage

    async def process_command(self, user_input: str) -> Optional[str]:
        """
        Process a command and return markdown result.
        Returns markdown string to display or None.
        """
        cmd_lower = user_input.strip().lower()
        
        # Handle basic commands
        if cmd_lower in ["help", "h", "?"]:
            return self._show_help()
        elif cmd_lower in ["exit", "quit", "q"]:
            self.app.exit()
            return None
        elif cmd_lower in ["clear", "cls"]:
            return ""
        elif cmd_lower == "status":
            return self._show_status()
        
        # Handle alpaca:backtest commands
        if cmd_lower.startswith("alpaca:backtest"):
            return await self._handle_backtest(user_input)
        
        return f"# Unknown Command\n\nCommand not recognized: `{user_input}`\n\nType 'help' for available commands."

    def _show_help(self) -> str:
        """Show help message."""
        return """# Strategy Simulator TUI - Help

## Command Format

### Alpaca Backtesting
```
alpaca:backtest strategy:<strategy_name> lookback:<period> [options]
```

### Required Parameters
- `strategy:<name>` - Strategy to backtest
  - `buy-the-dip` - Buy on price dips
  - `momentum` - Momentum trading
- `lookback:<period>` - Historical period
  - `1m`, `2m`, `3m`, `6m`, `1y`

### Optional Parameters
- `symbols:<TICKER1,TICKER2,...>` - Comma-separated tickers (default: Mag 7)
- `capital:<amount>` - Initial capital (default: 10000)
- `position:<pct>` - Position size percentage (default: 10)
- `dip:<pct>` - Dip threshold for buy-the-dip (default: 2.0)
- `hold:<days>` - Hold days (default: 1)
- `takeprofit:<pct>` - Take profit percentage (default: 1.0)
- `stoploss:<pct>` - Stop loss percentage (default: 0.5)
- `interval:<freq>` - Data frequency: 1d, 60m, 30m, 15m, 5m (default: 1d)

### Examples
```
alpaca:backtest strategy:buy-the-dip lookback:1m
alpaca:backtest strategy:momentum lookback:3m symbols:AAPL,TSLA
alpaca:backtest strategy:buy-the-dip lookback:6m capital:50000 position:15
alpaca:backtest strategy:buy-the-dip lookback:1m dip:3.0 takeprofit:2.0 stoploss:1.0
alpaca:backtest strategy:momentum lookback:1m interval:60m
```

### Other Commands
- `help` - Show this help
- `status` - Show current configuration
- `clear` - Clear results
- `q`, `exit`, `quit` - Exit application

### Keyboard Shortcuts
- `Ctrl+L` - Clear results
- `Ctrl+C` or `Q` - Quit
"""

    def _show_status(self) -> str:
        """Show current status and configuration."""
        return f"""# Current Configuration

## Default Settings
- **Symbols**: {', '.join(self.default_symbols)}
- **Initial Capital**: ${self.default_capital:,}
- **Position Size**: {self.default_position_size}%

## Recent Commands
{self._format_command_history()}

Type 'help' for available commands.
"""

    def _format_command_history(self) -> str:
        """Format command history."""
        if not self.app.command_history:
            return "No commands executed yet."
        
        history = self.app.command_history[-5:]  # Last 5 commands
        return "\n".join([f"{i+1}. `{cmd}`" for i, cmd in enumerate(history)])

    async def _handle_backtest(self, command: str) -> str:
        """Handle alpaca:backtest command."""
        try:
            # Parse command parameters
            params = self._parse_backtest_command(command)
            
            # Validate required parameters
            if 'strategy' not in params:
                return "# Error\n\nMissing required parameter: `strategy`\n\nExample: `alpaca:backtest strategy:buy-the-dip lookback:1m`"
            
            if 'lookback' not in params:
                return "# Error\n\nMissing required parameter: `lookback`\n\nExample: `alpaca:backtest strategy:buy-the-dip lookback:1m`"
            
            # Calculate date range from lookback
            end_date = datetime.now()
            lookback = params['lookback']
            start_date = self._calculate_start_date(end_date, lookback)
            
            # Get parameters with defaults
            strategy = params['strategy']
            symbols = params.get('symbols', self.default_symbols)
            initial_capital = params.get('capital', self.default_capital)
            position_size = params.get('position', self.default_position_size)
            interval = params.get('interval', '1d')
            
            # Strategy-specific parameters
            if strategy == 'buy-the-dip':
                dip_threshold = params.get('dip', 2.0)
                hold_days = params.get('hold', 1)
                take_profit = params.get('takeprofit', 1.0)
                stop_loss = params.get('stoploss', 0.5)
                data_source = params.get('data_source', 'massive').replace('polygon', 'massive').replace('polymarket', 'massive')
                
                # Run backtest
                result_md = await self._run_buy_the_dip_backtest(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    position_size=position_size,
                    dip_threshold=dip_threshold,
                    hold_days=hold_days,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    interval=interval,
                    data_source=data_source
                )
                return result_md
                
            elif strategy == 'momentum':
                lookback_period = params.get('lookback_period', 20)
                momentum_threshold = params.get('momentum_threshold', 5.0)
                hold_days = params.get('hold', 5)
                take_profit = params.get('takeprofit', 10.0)
                stop_loss = params.get('stoploss', 5.0)
                data_source = params.get('data_source', 'massive').replace('polygon', 'massive').replace('polymarket', 'massive')
                
                # Run backtest
                result_md = await self._run_momentum_backtest(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    position_size=position_size,
                    lookback_period=lookback_period,
                    momentum_threshold=momentum_threshold,
                    hold_days=hold_days,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    interval=interval,
                    data_source=data_source
                )
                return result_md
            else:
                return f"# Error\n\nUnknown strategy: `{strategy}`\n\nAvailable strategies: buy-the-dip, momentum"
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return f"# Error\n\n```\n{str(e)}\n\n{error_trace}\n```"

    def _parse_backtest_command(self, command: str) -> Dict[str, Any]:
        """Parse backtest command into parameters."""
        params = {}
        
        # Split by spaces but respect quoted strings
        parts = command.split()
        
        for part in parts[1:]:  # Skip 'alpaca:backtest'
            if ':' in part:
                key, value = part.split(':', 1)
                key = key.lower()
                
                if key == 'strategy':
                    params['strategy'] = value.lower()
                elif key == 'lookback':
                    params['lookback'] = value.lower()
                elif key == 'symbols':
                    params['symbols'] = [s.strip().upper() for s in value.split(',')]
                elif key == 'capital':
                    params['capital'] = float(value)
                elif key == 'position':
                    params['position'] = float(value)
                elif key == 'dip':
                    params['dip'] = float(value)
                elif key == 'hold':
                    params['hold'] = int(value)
                elif key == 'takeprofit':
                    params['takeprofit'] = float(value)
                elif key == 'stoploss':
                    params['stoploss'] = float(value)
                elif key == 'interval':
                    params['interval'] = value.lower()
                elif key == 'lookback_period':
                    params['lookback_period'] = int(value)
                elif key == 'momentum_threshold':
                    params['momentum_threshold'] = float(value)
                elif key == 'data_source':
                    params['data_source'] = value.lower()
        
        return params

    def _calculate_start_date(self, end_date: datetime, lookback: str) -> datetime:
        """Calculate start date from lookback period."""
        if lookback.endswith('m'):
            months = int(lookback[:-1])
            return end_date - timedelta(days=months * 30)
        elif lookback.endswith('y'):
            years = int(lookback[:-1])
            return end_date - timedelta(days=years * 365)
        else:
            raise ValueError(f"Invalid lookback format: {lookback}. Use format like '1m', '3m', '1y'")

    async def _run_buy_the_dip_backtest(
        self,
        symbols,
        start_date,
        end_date,
        initial_capital,
        position_size,
        dip_threshold,
        hold_days,
        take_profit,
        stop_loss,
        interval,
        data_source
    ) -> str:
        """Run buy-the-dip backtest and return markdown results."""
        from utils.backtester_util import backtest_buy_the_dip
        
        # Run backtest
        results = backtest_buy_the_dip(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            position_size=position_size / 100,
            dip_threshold=dip_threshold / 100,
            hold_days=hold_days,
            take_profit=take_profit / 100,
            stop_loss=stop_loss / 100,
            interval=interval,
            data_source=data_source,
            include_taf_fees=True,
            include_cat_fees=True
        )
        
        if results is not None:
            trades_df, _, _ = results  # Unpack all 3 values: trades_df, metrics, equity_curve
            from pathlib import Path
            output_dir = Path("backtest-results")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtests_details_buy_the_dip_{timestamp}.csv"
            trades_df.to_csv(output_dir / filename, index=False)
        
        if results is None:
            return "# No Results\n\nNo trades were generated during the backtest period. Try adjusting parameters or date range."
        
        trades_df, metrics, _ = results  # Unpack all 3 values
        
        # Format results as markdown
        return self._format_backtest_results(
            strategy="Buy-The-Dip",
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            trades_df=trades_df,
            metrics=metrics,
            params={
                'Position Size': f"{position_size}%",
                'Dip Threshold': f"{dip_threshold}%",
                'Hold Days': hold_days,
                'Take Profit': f"{take_profit}%",
                'Stop Loss': f"{stop_loss}%",
                'Interval': interval
            }
        )

    async def _run_momentum_backtest(
        self,
        symbols,
        start_date,
        end_date,
        initial_capital,
        position_size,
        lookback_period,
        momentum_threshold,
        hold_days,
        take_profit,
        stop_loss,
        interval,
        data_source
    ) -> str:
        """Run momentum backtest and return markdown results."""
        from utils.backtester_util import backtest_momentum_strategy
        
        # Run backtest
        results = backtest_momentum_strategy(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            position_size_pct=position_size,
            lookback_period=lookback_period,
            momentum_threshold=momentum_threshold,
            hold_days=hold_days,
            take_profit_pct=take_profit,
            stop_loss_pct=stop_loss,
            interval=interval,
            data_source=data_source,
            include_taf_fees=True,
            include_cat_fees=True
        )
        
        if results is not None:
            trades_df, _, _ = results  # Unpack all 3 values: trades_df, metrics, equity_curve
            from pathlib import Path
            output_dir = Path("backtest-results")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtests_details_momentum_{timestamp}.csv"
            trades_df.to_csv(output_dir / filename, index=False)
        
        if results is None:
            return "# No Results\n\nNo trades were generated during the backtest period. Try adjusting parameters or date range."
        
        trades_df, metrics, _ = results  # Unpack all 3 values
        
        # Format results as markdown
        return self._format_backtest_results(
            strategy="Momentum",
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            trades_df=trades_df,
            metrics=metrics,
            params={
                'Position Size': f"{position_size}%",
                'Lookback Period': f"{lookback_period} days",
                'Momentum Threshold': f"{momentum_threshold}%",
                'Hold Days': hold_days,
                'Take Profit': f"{take_profit}%",
                'Stop Loss': f"{stop_loss}%",
                'Interval': interval
            }
        )

    def _format_backtest_results(
        self,
        strategy: str,
        symbols,
        start_date,
        end_date,
        initial_capital,
        trades_df,
        metrics,
        params
    ) -> str:
        """Format backtest results as markdown."""
        
        # Header
        md = f"# {strategy} Strategy Backtest Results\n\n"
        
        # Configuration
        md += "## Configuration\n\n"
        md += f"- **Symbols**: {', '.join(symbols)}\n"
        md += f"- **Period**: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
        md += f"- **Initial Capital**: ${initial_capital:,.2f}\n"
        
        for key, value in params.items():
            md += f"- **{key}**: {value}\n"
        
        md += "\n"
        
        # Performance Metrics
        md += "## Performance Metrics\n\n"
        md += "| Metric | Value |\n"
        md += "|--------|-------|\n"
        md += f"| Total Return | {metrics['total_return']:.2f}% |\n"
        md += f"| Total P&L | ${metrics['total_pnl']:,.2f} |\n"
        md += f"| Annualized Return | {metrics['annualized_return']:.2f}% |\n"
        md += f"| Total Trades | {metrics['total_trades']} |\n"
        md += f"| Win Rate | {metrics['win_rate']:.1f}% |\n"
        md += f"| Winning Trades | {metrics['winning_trades']} |\n"
        md += f"| Losing Trades | {metrics['losing_trades']} |\n"
        md += f"| Max Drawdown | {metrics['max_drawdown']:.2f}% |\n"
        md += f"| Sharpe Ratio | {metrics['sharpe_ratio']:.2f} |\n"
        md += "\n"
        
        # Recent Trades (last 10)
        md += "## Recent Trades (Last 10)\n\n"
        recent_trades = trades_df.tail(10)
        
        md += "| Entry Time | Exit Time | Ticker | Shares | Entry $ | Exit $ | P&L | P&L % |\n"
        md += "|------------|-----------|--------|--------|---------|--------|-----|-------|\n"
        
        for _, trade in recent_trades.iterrows():
            entry_time = pd.to_datetime(trade['entry_time']).strftime('%Y-%m-%d %H:%M')
            exit_time = pd.to_datetime(trade['exit_time']).strftime('%Y-%m-%d %H:%M')
            md += f"| {entry_time} | {exit_time} | {trade['ticker']} | {trade['shares']} | "
            md += f"${trade['entry_price']:.2f} | ${trade['exit_price']:.2f} | "
            md += f"${trade['pnl']:.2f} | {trade['pnl_pct']:.2f}% |\n"
        
        md += "\n"
        
        # Summary
        final_capital = trades_df['capital_after'].iloc[-1]
        md += "## Summary\n\n"
        md += f"Starting with **${initial_capital:,.2f}**, the {strategy} strategy generated "
        md += f"**{metrics['total_trades']}** trades over the period, resulting in a "
        md += f"**{metrics['total_return']:.2f}%** return (${metrics['total_pnl']:,.2f}). "
        md += f"Final portfolio value: **${final_capital:,.2f}**.\n\n"
        
        if metrics['win_rate'] > 50:
            md += f"✅ The strategy achieved a **{metrics['win_rate']:.1f}%** win rate with "
            md += f"{metrics['winning_trades']} winning trades.\n"
        else:
            md += f"⚠️ The strategy had a **{metrics['win_rate']:.1f}%** win rate with "
            md += f"{metrics['winning_trades']} winning trades and {metrics['losing_trades']} losing trades.\n"
        
        return md
