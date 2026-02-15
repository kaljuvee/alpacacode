"""
Command Processor for Strategy Simulator TUI
Handles command parsing and execution for both legacy backtests and the
multi-agent orchestrator framework.
"""
import sys
import asyncio
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from rich.console import Console

# Ensure project root is importable
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class CommandProcessor:
    """Processes commands for the Strategy Simulator TUI."""

    def __init__(self, app_instance):
        self.app = app_instance
        self.console = Console()

        # Default parameters
        self.default_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
        self.default_capital = 10000
        self.default_position_size = 10  # percentage

        # Agent state (shared across calls via app instance)
        if not hasattr(self.app, '_orch'):
            self.app._orch = None
        if not hasattr(self.app, '_bg_task'):
            self.app._bg_task = None
        if not hasattr(self.app, '_bg_stop'):
            self.app._bg_stop = threading.Event()

    # ------------------------------------------------------------------
    # Main dispatcher
    # ------------------------------------------------------------------

    async def process_command(self, user_input: str) -> Optional[str]:
        """
        Process a command and return markdown result.
        Returns markdown string to display or None.
        """
        cmd_lower = user_input.strip().lower()

        # Basic commands
        if cmd_lower in ["help", "h", "?"]:
            return self._show_help()
        elif cmd_lower in ["exit", "quit", "q"]:
            if hasattr(self.app, 'exit'):
                self.app.exit()
            return None
        elif cmd_lower in ["clear", "cls"]:
            return ""
        elif cmd_lower == "status":
            return self._show_status()
        elif cmd_lower == "trades":
            return self._agent_trades({})
        elif cmd_lower == "runs":
            return self._agent_runs()

        # Legacy backtest commands
        if cmd_lower.startswith("alpaca:backtest"):
            return await self._handle_backtest(user_input)

        # Agent framework commands
        if cmd_lower.startswith("agent:"):
            return await self._handle_agent_command(user_input)

        return (
            f"# Unknown Command\n\nCommand not recognized: `{user_input}`\n\n"
            "Type 'help' for available commands."
        )

    # ------------------------------------------------------------------
    # Agent command dispatcher
    # ------------------------------------------------------------------

    async def _handle_agent_command(self, user_input: str) -> str:
        """Dispatch agent:* commands."""
        parts = user_input.strip().split()
        subcmd = parts[0].lower()
        params = self._parse_kv_params(parts[1:])

        if subcmd == "agent:backtest":
            return await self._agent_backtest(params)
        elif subcmd == "agent:validate":
            return await self._agent_validate(params)
        elif subcmd == "agent:paper":
            return await self._agent_paper(params)
        elif subcmd == "agent:full":
            return await self._agent_full(params)
        elif subcmd == "agent:reconcile":
            return await self._agent_reconcile(params)
        elif subcmd == "agent:status":
            return self._agent_status()
        elif subcmd == "agent:runs":
            return self._agent_runs()
        elif subcmd == "agent:trades":
            return self._agent_trades(params)
        elif subcmd == "agent:report":
            return self._agent_report(params)
        elif subcmd == "agent:stop":
            return self._agent_stop()
        else:
            return (
                f"# Unknown Agent Command\n\n`{subcmd}` is not recognized.\n\n"
                "Available: `agent:backtest`, `agent:validate`, `agent:paper`, "
                "`agent:full`, `agent:reconcile`, `agent:report`, `agent:status`, "
                "`agent:runs`, `agent:trades`, `agent:stop`"
            )

    def _parse_kv_params(self, parts: list) -> Dict[str, str]:
        """Parse key:value pairs from command parts."""
        params = {}
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                params[key.lower()] = value
        return params

    def _get_orchestrator(self) -> "Orchestrator":
        """Get or create an Orchestrator instance."""
        from agents.orchestrator import Orchestrator
        if self.app._orch is None:
            self.app._orch = Orchestrator()
        return self.app._orch

    def _new_orchestrator(self) -> "Orchestrator":
        """Create a fresh Orchestrator (new run_id, clean state)."""
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        # Clear stale state loaded from disk so status shows current run only
        orch.state.mode = None
        orch.state.best_config = None
        orch.state.validation_results = []
        self.app._orch = orch
        return orch

    # ------------------------------------------------------------------
    # agent:backtest
    # ------------------------------------------------------------------

    async def _agent_backtest(self, params: Dict) -> str:
        """Run orchestrator backtest mode."""
        from agents.orchestrator import parse_duration

        orch = self._new_orchestrator()
        symbols_str = params.get("symbols", ",".join(self.default_symbols))
        symbols = [s.strip().upper() for s in symbols_str.split(",")]

        # PDT protection: default True (None lets strategy decide), pdt:false disables
        pdt_val = params.get("pdt")
        pdt_protection = None  # let strategy default (True if capital < $25k)
        if pdt_val is not None:
            pdt_protection = pdt_val.lower() not in ("false", "no", "0", "off")

        config = {
            "strategy": params.get("strategy", "buy_the_dip"),
            "symbols": symbols,
            "lookback": params.get("lookback", "3m"),
            "initial_capital": float(params.get("capital", self.default_capital)),
            "extended_hours": params.get("hours") == "extended",
            "intraday_exit": params.get("intraday_exit", "false").lower() in ("true", "yes", "1", "on"),
            "pdt_protection": pdt_protection,
        }

        result = await asyncio.to_thread(orch.run_backtest, config)

        if "error" in result:
            return f"# Backtest Failed\n\n```\n{result['error']}\n```"

        best = result.get("best_config", {})
        p = best.get("params", {})
        run_id = result.get('run_id', '')

        # Pre-fill the next prompt with the validate command
        if hasattr(self.app, '_suggested_command'):
            self.app._suggested_command = f"agent:validate run-id:{run_id}"

        return (
            f"# Backtest Complete\n\n"
            f"- **Run ID**: `{run_id}`\n"
            f"- **Strategy**: {result.get('strategy')}\n"
            f"- **Variations**: {result.get('total_variations')}\n\n"
            f"## Best Configuration\n\n"
            f"| Metric | Value |\n|--------|-------|\n"
            f"| Sharpe Ratio | {best.get('sharpe_ratio', 0):.2f} |\n"
            f"| Total Return | {best.get('total_return', 0):.1f}% |\n"
            f"| Annualized Return | {best.get('annualized_return', 0):.1f}% |\n"
            f"| Total P&L | ${best.get('total_pnl', 0):,.2f} |\n"
            f"| Win Rate | {best.get('win_rate', 0):.1f}% |\n"
            f"| Total Trades | {best.get('total_trades', 0)} |\n"
            f"| Max Drawdown | {best.get('max_drawdown', 0):.2f}% |\n\n"
            f"**Params**: dip={p.get('dip_threshold')}, "
            f"tp={p.get('take_profit')}, hold={p.get('hold_days')}\n\n"
            f"Press Enter to validate, or type a new command."
        )

    # ------------------------------------------------------------------
    # agent:validate
    # ------------------------------------------------------------------

    async def _agent_validate(self, params: Dict) -> str:
        """Run validation against a run."""
        run_id = params.get("run-id")
        source = params.get("source", "backtest")

        orch = self._get_orchestrator()
        result = await asyncio.to_thread(
            orch.run_validation, run_id=run_id, source=source
        )

        if "error" in result:
            return f"# Validation Failed\n\n```\n{result['error']}\n```"

        status = result.get("status", "unknown")
        suggestions_md = ""
        if result.get("suggestions"):
            suggestions_md = "\n## Suggestions\n" + "\n".join(
                f"- {s}" for s in result["suggestions"]
            )

        return (
            f"# Validation: {status.upper()}\n\n"
            f"| Metric | Value |\n|--------|-------|\n"
            f"| Status | {status} |\n"
            f"| Anomalies Found | {result.get('anomalies_found', 0)} |\n"
            f"| Anomalies Corrected | {result.get('anomalies_corrected', 0)} |\n"
            f"| Iterations Used | {result.get('iterations_used', 0)} |\n"
            f"{suggestions_md}"
        )

    # ------------------------------------------------------------------
    # agent:paper (background)
    # ------------------------------------------------------------------

    async def _agent_paper(self, params: Dict) -> str:
        """Start paper trading in the background."""
        from agents.orchestrator import parse_duration

        if self.app._bg_task and not self.app._bg_task.done():
            return (
                "# Paper Trading Already Running\n\n"
                "Use `agent:stop` to cancel, or `agent:status` to check progress."
            )

        orch = self._new_orchestrator()
        orch._mode = "paper"  # set eagerly so agent:status shows correct mode
        self.app._bg_stop.clear()

        symbols_str = params.get("symbols", ",".join(self.default_symbols))
        symbols = [s.strip().upper() for s in symbols_str.split(",")]
        duration = params.get("duration", "7d")

        # PDT protection
        pdt_val = params.get("pdt")
        pdt_protection = None
        if pdt_val is not None:
            pdt_protection = pdt_val.lower() not in ("false", "no", "0", "off")

        config = {
            "strategy": params.get("strategy", "buy_the_dip"),
            "symbols": symbols,
            "duration_seconds": parse_duration(duration),
            "poll_interval_seconds": int(params.get("poll", "300")),
            "extended_hours": params.get("hours") == "extended",
            "email_notifications": params.get("email", "true").lower() not in ("false", "no", "0", "off"),
            "pdt_protection": pdt_protection,
        }

        run_id = orch.run_id

        async def _run_paper():
            result = await asyncio.to_thread(orch.run_paper_trade, config)
            # Notify TUI when done
            if hasattr(self.app, 'notify'):
                trades = result.get("total_trades", 0)
                pnl = result.get("total_pnl", 0)
                self.app.notify(
                    f"Paper trading done: {trades} trades, P&L: ${pnl:.2f}"
                )

        self.app._bg_task = asyncio.create_task(_run_paper())

        return (
            f"# Paper Trading Started\n\n"
            f"- **Run ID**: `{run_id}`\n"
            f"- **Duration**: {duration}\n"
            f"- **Strategy**: {config['strategy']}\n"
            f"- **Symbols**: {', '.join(symbols)}\n"
            f"- **Poll Interval**: {config['poll_interval_seconds']}s\n\n"
            f"Running in background. Use `agent:status` to monitor, "
            f"`agent:stop` to cancel."
        )

    # ------------------------------------------------------------------
    # agent:full
    # ------------------------------------------------------------------

    async def _agent_full(self, params: Dict) -> str:
        """Run full cycle: backtest -> validate -> paper -> validate."""
        from agents.orchestrator import parse_duration

        orch = self._new_orchestrator()
        symbols_str = params.get("symbols", ",".join(self.default_symbols))
        symbols = [s.strip().upper() for s in symbols_str.split(",")]
        duration = params.get("duration", "1m")

        # PDT protection
        pdt_val = params.get("pdt")
        pdt_protection = None
        if pdt_val is not None:
            pdt_protection = pdt_val.lower() not in ("false", "no", "0", "off")

        config = {
            "strategy": params.get("strategy", "buy_the_dip"),
            "symbols": symbols,
            "lookback": params.get("lookback", "3m"),
            "initial_capital": float(params.get("capital", self.default_capital)),
            "duration_seconds": parse_duration(duration),
            "poll_interval_seconds": int(params.get("poll", "300")),
            "extended_hours": params.get("hours") == "extended",
            "intraday_exit": params.get("intraday_exit", "false").lower() in ("true", "yes", "1", "on"),
            "pdt_protection": pdt_protection,
        }

        result = await asyncio.to_thread(orch.run_full, config)

        status = result.get("status", "unknown")
        phases = result.get("phases", {})

        md = f"# Full Cycle: {status.upper()}\n\n"
        md += f"- **Run ID**: `{result.get('run_id', '')}`\n\n"

        # Backtest phase
        bt = phases.get("backtest", {})
        if bt and "error" not in bt:
            best = bt.get("best_config", {})
            md += (
                f"## Backtest\n"
                f"- Variations: {bt.get('total_variations')}\n"
                f"- Best Sharpe: {best.get('sharpe_ratio', 0):.2f}\n"
                f"- Best Return: {best.get('total_return', 0):.1f}%\n\n"
            )

        # Backtest validation
        bv = phases.get("backtest_validation", {})
        if bv:
            md += (
                f"## Backtest Validation: {bv.get('status', 'n/a')}\n"
                f"- Anomalies: {bv.get('anomalies_found', 0)} found, "
                f"{bv.get('anomalies_corrected', 0)} corrected\n\n"
            )

        # Paper trade
        pt = phases.get("paper_trade", {})
        if pt and "error" not in pt:
            md += (
                f"## Paper Trade\n"
                f"- Trades: {pt.get('total_trades', 0)}\n"
                f"- P&L: ${pt.get('total_pnl', 0):.2f}\n\n"
            )

        # Paper validation
        pv = phases.get("paper_trade_validation", {})
        if pv:
            md += (
                f"## Paper Validation: {pv.get('status', 'n/a')}\n"
                f"- Anomalies: {pv.get('anomalies_found', 0)} found\n"
            )

        return md

    # ------------------------------------------------------------------
    # agent:reconcile
    # ------------------------------------------------------------------

    async def _agent_reconcile(self, params: Dict) -> str:
        """Run reconciliation against Alpaca actual holdings."""
        orch = self._new_orchestrator()

        window_str = params.get("window", "7d")
        # Parse window: "7d" -> 7
        window_days = int(window_str.rstrip("d")) if window_str.endswith("d") else int(window_str)

        config = {"window_days": window_days}
        result = await asyncio.to_thread(orch.run_reconciliation, config)

        if "error" in result:
            return f"# Reconciliation Failed\n\n```\n{result['error']}\n```"

        status = result.get("status", "unknown")
        total_issues = result.get("total_issues", 0)

        md = f"# Reconciliation: {status.upper()}\n\n"
        md += f"- **Total Issues**: {total_issues}\n\n"

        # Position mismatches
        pos = result.get("position_mismatches", [])
        if pos:
            md += "## Position Mismatches\n\n"
            md += "| Type | Symbol | Details |\n|------|--------|---------|\n"
            for p in pos:
                md += f"| {p.get('type', '')} | {p.get('symbol', '')} | {p.get('message', '')} |\n"
            md += "\n"

        # Missing trades (in Alpaca not in DB)
        missing = result.get("missing_trades", [])
        if missing:
            md += f"## Missing Trades ({len(missing)} in Alpaca, not in DB)\n\n"
            md += "| Symbol | Side | Qty | Filled At |\n|--------|------|-----|-----------|\n"
            for t in missing[:20]:
                md += f"| {t.get('symbol', '')} | {t.get('side', '')} | {t.get('qty', '')} | {str(t.get('filled_at', ''))[:19]} |\n"
            md += "\n"

        # Extra trades (in DB not in Alpaca)
        extra = result.get("extra_trades", [])
        if extra:
            md += f"## Extra Trades ({len(extra)} in DB, not in Alpaca)\n\n"
            md += "| Symbol | Side | Message |\n|--------|------|---------|\n"
            for t in extra[:20]:
                md += f"| {t.get('symbol', '')} | {t.get('side', '')} | {t.get('message', '')} |\n"
            md += "\n"

        # P&L comparison
        pnl = result.get("pnl_comparison", {})
        if pnl:
            md += "## P&L Comparison\n\n"
            md += "| Metric | Value |\n|--------|-------|\n"
            md += f"| Alpaca Equity | ${pnl.get('alpaca_equity', 0):,.2f} |\n"
            md += f"| Alpaca Cash | ${pnl.get('alpaca_cash', 0):,.2f} |\n"
            md += f"| Alpaca Portfolio Value | ${pnl.get('alpaca_portfolio_value', 0):,.2f} |\n"
            md += f"| DB Total P&L | ${pnl.get('db_total_pnl', 0):,.2f} |\n"

        return md

    # ------------------------------------------------------------------
    # agent:status
    # ------------------------------------------------------------------

    def _agent_status(self) -> str:
        """Show current agent states."""
        orch = self.app._orch
        if orch is None:
            return "# Agent Status\n\nNo session active. Run an `agent:*` command first.\n"

        # Use instance mode (not persisted state which may be stale)
        mode = getattr(orch, '_mode', None) or orch.state.mode or 'n/a'
        bg_running = self.app._bg_task and not self.app._bg_task.done()
        bg_done = self.app._bg_task and self.app._bg_task.done()

        # Header with status
        if bg_running:
            status_label = "RUNNING"
        elif bg_done:
            status_label = "COMPLETED"
        else:
            status_label = "IDLE"

        md = f"# {mode.replace('_', ' ').title()} — {status_label}\n\n"
        md += f"- **Run ID**: `{orch.run_id}`\n"

        # Show started time in ET
        from utils.tz_util import format_et
        started = orch.state.started_at or 'n/a'
        if started != 'n/a':
            started = format_et(started)
        md += f"- **Started**: {started}\n\n"

        # Agents table — only show agents relevant to the mode
        md += "| Agent | Status | Task |\n|-------|--------|------|\n"
        for name, agent in orch.state.agents.items():
            md += f"| {name} | {agent.status} | {agent.current_task or '-'} |\n"

        # Best config (only for modes that involve backtesting)
        if orch.state.best_config and mode in ('backtest', 'full'):
            best = orch.state.best_config
            md += (
                f"\n## Best Config\n"
                f"- Sharpe: {best.get('sharpe_ratio', 0):.2f}\n"
                f"- Return: {best.get('total_return', 0):.1f}%\n"
                f"- Annualized: {best.get('annualized_return', 0):.1f}%\n"
            )

        # Last validation (only if we ran validation)
        if orch.state.validation_results and mode in ('validate', 'full'):
            last = orch.state.validation_results[-1]
            md += (
                f"\n## Last Validation\n"
                f"- Status: {last.get('status')}\n"
                f"- Anomalies: {last.get('anomalies_found', 0)}\n"
            )

        return md

    # ------------------------------------------------------------------
    # agent:runs (DB query)
    # ------------------------------------------------------------------

    def _agent_runs(self) -> str:
        """List recent runs from alpacacode.runs."""
        try:
            from utils.db.db_pool import DatabasePool
            from sqlalchemy import text

            pool = DatabasePool()
            with pool.get_session() as session:
                result = session.execute(
                    text("""
                        SELECT run_id, mode, strategy, status, started_at, completed_at
                        FROM alpacacode.runs
                        ORDER BY created_at DESC
                        LIMIT 20
                    """)
                )
                rows = result.fetchall()

            if not rows:
                return "# Runs\n\nNo runs found in database."

            from utils.tz_util import format_et
            md = "# Recent Runs\n\n"
            md += "| Run ID | Mode | Strategy | Status | Started (ET) |\n"
            md += "|--------|------|----------|--------|--------------|\n"
            for r in rows:
                short_id = str(r[0])[:8]
                started = format_et(r[4]) if r[4] else "-"
                md += f"| `{short_id}...` | {r[1]} | {r[2] or '-'} | {r[3]} | {started} |\n"

            md += f"\n*{len(rows)} runs shown*"
            return md

        except Exception as e:
            return f"# Error\n\n```\n{e}\n```"

    # ------------------------------------------------------------------
    # agent:trades (DB query)
    # ------------------------------------------------------------------

    def _agent_trades(self, params: Dict) -> str:
        """Query trades from alpacacode.trades."""
        try:
            from utils.db.db_pool import DatabasePool
            from sqlalchemy import text

            run_id = params.get("run-id")
            trade_type = params.get("type")
            limit = int(params.get("limit", "20"))

            pool = DatabasePool()
            with pool.get_session() as session:
                where_clauses = []
                bind = {}
                if run_id:
                    where_clauses.append("run_id = :run_id")
                    bind["run_id"] = run_id
                if trade_type:
                    where_clauses.append("trade_type = :trade_type")
                    bind["trade_type"] = trade_type

                where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

                result = session.execute(
                    text(f"""
                        SELECT symbol, direction, shares, entry_price, exit_price,
                               pnl, pnl_pct, trade_type, run_id
                        FROM alpacacode.trades
                        {where_sql}
                        ORDER BY created_at DESC
                        LIMIT :lim
                    """),
                    {**bind, "lim": limit},
                )
                rows = result.fetchall()

            if not rows:
                return "# Trades\n\nNo trades found."

            md = "# Trades\n\n"
            md += "| Symbol | Dir | Shares | Entry | Exit | P&L | P&L% | Type |\n"
            md += "|--------|-----|--------|-------|------|-----|------|------|\n"
            for r in rows:
                pnl_str = f"${float(r[5] or 0):.2f}"
                pct_str = f"{float(r[6] or 0):.2f}%"
                md += (
                    f"| {r[0]} | {r[1]} | {float(r[2] or 0):.0f} | "
                    f"${float(r[3] or 0):.2f} | ${float(r[4] or 0):.2f} | "
                    f"{pnl_str} | {pct_str} | {r[7]} |\n"
                )

            md += f"\n*{len(rows)} trades shown*"
            return md

        except Exception as e:
            return f"# Error\n\n```\n{e}\n```"

    # ------------------------------------------------------------------
    # agent:report
    # ------------------------------------------------------------------

    def _agent_report(self, params: Dict) -> str:
        """Generate performance report from DB data."""
        try:
            from agents.report_agent import ReportAgent
            from utils.tz_util import format_et

            agent = ReportAgent()
            run_id = params.get("run-id")

            # Detail mode: single run
            if run_id:
                data = agent.detail(run_id)
                if not data:
                    return f"# Report\n\nRun `{run_id}` not found."

                short_id = str(data["run_id"])[:8]
                started = format_et(data["started_at"], "%b %-d") if data["started_at"] else "-"
                ended = format_et(data["completed_at"], "%b %-d") if data["completed_at"] else "-"
                w = data["winning_trades"]
                l = data["losing_trades"]

                md = f"# Report: {short_id}...\n\n"
                md += "| Metric | Value |\n|--------|-------|\n"
                md += f"| Mode | {data['mode']} |\n"
                md += f"| Strategy | {data['strategy'] or '-'} |\n"
                md += f"| Status | {data['status']} |\n"
                md += f"| Initial Capital | ${data['initial_capital']:,.2f} |\n"
                md += f"| Final Capital | ${data['final_capital']:,.2f} |\n"
                md += f"| Total P&L | ${data['total_pnl']:,.2f} |\n"
                md += f"| Total Return | {data['total_return']:.2f}% |\n"
                md += f"| Annualized Return | {data['annualized_return']:.2f}% |\n"
                md += f"| Sharpe Ratio | {data['sharpe_ratio']:.2f} |\n"
                md += f"| Max Drawdown | {data['max_drawdown']:.2f}% |\n"
                md += f"| Win Rate | {data['win_rate']:.1f}% |\n"
                md += f"| Trades (W/L) | {data['total_trades']} ({w}W / {l}L) |\n"
                md += f"| Period | {started} → {ended} |\n"
                return md

            # Summary mode: list of runs
            trade_type = params.get("type")
            limit = int(params.get("limit", "10"))
            rows = agent.summary(trade_type=trade_type, limit=limit)

            if not rows:
                return "# Performance Summary\n\nNo runs found."

            md = "# Performance Summary\n\n"
            md += "| Run ID | Mode | Strategy | P&L | Return | Sharpe | Trades | Status |\n"
            md += "|--------|------|----------|-----|--------|--------|--------|--------|\n"
            for r in rows:
                short_id = str(r["run_id"])[:8]
                pnl_str = f"${r['total_pnl']:,.2f}"
                ret_str = f"{r['total_return']:.1f}%"
                sharpe_str = f"{r['sharpe_ratio']:.2f}" if r["sharpe_ratio"] else "-"
                md += (
                    f"| `{short_id}...` | {r['mode']} | {r['strategy'] or '-'} | "
                    f"{pnl_str} | {ret_str} | {sharpe_str} | "
                    f"{r['total_trades']} | {r['status']} |\n"
                )

            md += f"\n*{len(rows)} runs shown*"
            return md

        except Exception as e:
            return f"# Error\n\n```\n{e}\n```"

    # ------------------------------------------------------------------
    # agent:stop
    # ------------------------------------------------------------------

    def _agent_stop(self) -> str:
        """Stop background paper trading."""
        if self.app._bg_task and not self.app._bg_task.done():
            self.app._bg_stop.set()
            self.app._bg_task.cancel()
            return "# Paper Trading Stopped\n\nBackground task cancelled."
        return "# No Background Task\n\nNo paper trading session is currently running."

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _show_help(self) -> str:
        """Show help as compact Rich tables."""
        from rich.table import Table
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.text import Text

        c = self.console

        c.print()
        c.print("[bold cyan]AlpacaCode CLI — Help[/bold cyan]")
        c.print()

        # --- Column 1: Agent commands ---
        col1 = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        col1.add_column(style="bold yellow", no_wrap=True)
        col1.add_column(style="dim")

        col1.add_row("[bold white]Backtest[/bold white]", "")
        col1.add_row("agent:backtest lookback:1m", "1-month backtest")
        col1.add_row("  symbols:AAPL,TSLA", "custom symbols")
        col1.add_row("  hours:extended", "pre/after-market")
        col1.add_row("  intraday_exit:true", "5-min TP/SL bars")
        col1.add_row("  pdt:false", "disable PDT rule")
        col1.add_row("", "")
        col1.add_row("[bold white]Validate[/bold white]", "")
        col1.add_row("agent:validate run-id:<uuid>", "validate a run")
        col1.add_row("  source:paper_trade", "validate paper trades")
        col1.add_row("", "")
        col1.add_row("[bold white]Reconcile[/bold white]", "")
        col1.add_row("agent:reconcile", "DB vs Alpaca (7d)")
        col1.add_row("  window:14d", "custom window")

        # --- Column 2: Paper / Full / Query ---
        col2 = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        col2.add_column(style="bold yellow", no_wrap=True)
        col2.add_column(style="dim")

        col2.add_row("[bold white]Paper Trade[/bold white]", "")
        col2.add_row("agent:paper duration:7d", "run in background")
        col2.add_row("  symbols:AAPL,MSFT poll:60", "custom config")
        col2.add_row("  hours:extended", "extended hours")
        col2.add_row("  email:false", "disable email reports")
        col2.add_row("  pdt:false", "disable PDT rule")
        col2.add_row("", "")
        col2.add_row("[bold white]Full Cycle[/bold white]", "BT > Val > PT > Val")
        col2.add_row("agent:full lookback:1m duration:1m", "")
        col2.add_row("  hours:extended", "extended hours")
        col2.add_row("", "")
        col2.add_row("[bold white]Query & Monitor[/bold white]", "")
        col2.add_row("trades / runs", "DB tables")
        col2.add_row("agent:report", "performance summary")
        col2.add_row("  type:backtest run-id:<uuid>", "filter / detail")
        col2.add_row("agent:status", "agent states")

        # --- Column 3: Options & params ---
        col3 = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        col3.add_column(style="bold yellow", no_wrap=True)
        col3.add_column(style="dim")

        col3.add_row("[bold white]Options[/bold white]", "")
        col3.add_row("hours:regular", "9:30AM-4PM ET (default)")
        col3.add_row("hours:extended", "4AM-8PM ET")
        col3.add_row("intraday_exit:true", "5-min bar exits")
        col3.add_row("pdt:false", "disable PDT (>$25k)")
        col3.add_row("email:false", "no daily P&L emails")
        col3.add_row("", "")
        col3.add_row("[bold white]Parameters[/bold white]", "")
        col3.add_row("lookback:1m|3m|6m|1y", "backtest period")
        col3.add_row("strategy:buy_the_dip", "strategy name")
        col3.add_row("symbols:AAPL,TSLA", "comma-separated")
        col3.add_row("capital:10000", "initial capital")
        col3.add_row("", "")
        col3.add_row("[bold white]General[/bold white]", "")
        col3.add_row("help / status / q", "")

        c.print(Columns([col1, col2, col3], equal=True, expand=True))
        c.print()
        return ""

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

        history = self.app.command_history[-5:]
        return "\n".join([f"{i+1}. `{cmd}`" for i, cmd in enumerate(history)])

    # ------------------------------------------------------------------
    # Legacy backtest handlers (unchanged)
    # ------------------------------------------------------------------

    async def _handle_backtest(self, command: str) -> str:
        """Handle alpaca:backtest command."""
        try:
            params = self._parse_backtest_command(command)

            if 'strategy' not in params:
                return "# Error\n\nMissing required parameter: `strategy`\n\nExample: `alpaca:backtest strategy:buy-the-dip lookback:1m`"
            if 'lookback' not in params:
                return "# Error\n\nMissing required parameter: `lookback`\n\nExample: `alpaca:backtest strategy:buy-the-dip lookback:1m`"

            end_date = datetime.now()
            lookback = params['lookback']
            start_date = self._calculate_start_date(end_date, lookback)

            strategy = params['strategy']
            symbols = params.get('symbols', self.default_symbols)
            initial_capital = params.get('capital', self.default_capital)
            position_size = params.get('position', self.default_position_size)
            interval = params.get('interval', '1d')

            if strategy == 'buy-the-dip':
                dip_threshold = params.get('dip', 2.0)
                hold_days = params.get('hold', 1)
                take_profit = params.get('takeprofit', 1.0)
                stop_loss = params.get('stoploss', 0.5)
                data_source = params.get('data_source', 'massive').replace('polygon', 'massive').replace('polymarket', 'massive')

                return await self._run_buy_the_dip_backtest(
                    symbols=symbols, start_date=start_date, end_date=end_date,
                    initial_capital=initial_capital, position_size=position_size,
                    dip_threshold=dip_threshold, hold_days=hold_days,
                    take_profit=take_profit, stop_loss=stop_loss,
                    interval=interval, data_source=data_source
                )

            elif strategy == 'momentum':
                lookback_period = params.get('lookback_period', 20)
                momentum_threshold = params.get('momentum_threshold', 5.0)
                hold_days = params.get('hold', 5)
                take_profit = params.get('takeprofit', 10.0)
                stop_loss = params.get('stoploss', 5.0)
                data_source = params.get('data_source', 'massive').replace('polygon', 'massive').replace('polymarket', 'massive')

                return await self._run_momentum_backtest(
                    symbols=symbols, start_date=start_date, end_date=end_date,
                    initial_capital=initial_capital, position_size=position_size,
                    lookback_period=lookback_period, momentum_threshold=momentum_threshold,
                    hold_days=hold_days, take_profit=take_profit, stop_loss=stop_loss,
                    interval=interval, data_source=data_source
                )
            else:
                return f"# Error\n\nUnknown strategy: `{strategy}`\n\nAvailable strategies: buy-the-dip, momentum"

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return f"# Error\n\n```\n{str(e)}\n\n{error_trace}\n```"

    def _parse_backtest_command(self, command: str) -> Dict[str, Any]:
        """Parse backtest command into parameters."""
        params = {}
        parts = command.split()

        for part in parts[1:]:
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

    async def _run_buy_the_dip_backtest(self, symbols, start_date, end_date,
                                         initial_capital, position_size,
                                         dip_threshold, hold_days, take_profit,
                                         stop_loss, interval, data_source) -> str:
        """Run buy-the-dip backtest and return markdown results."""
        from utils.backtester_util import backtest_buy_the_dip
        import pandas as pd

        results = backtest_buy_the_dip(
            symbols=symbols, start_date=start_date, end_date=end_date,
            initial_capital=initial_capital, position_size=position_size / 100,
            dip_threshold=dip_threshold / 100, hold_days=hold_days,
            take_profit=take_profit / 100, stop_loss=stop_loss / 100,
            interval=interval, data_source=data_source,
            include_taf_fees=True, include_cat_fees=True
        )

        if results is not None:
            trades_df, _, _ = results
            output_dir = Path("backtest-results")
            output_dir.mkdir(exist_ok=True)
            from utils.tz_util import now_et
            timestamp = now_et().strftime("%Y%m%d_%H%M%S")
            filename = f"backtests_details_buy_the_dip_{timestamp}.csv"
            trades_df.to_csv(output_dir / filename, index=False)

        if results is None:
            return "# No Results\n\nNo trades were generated. Try adjusting parameters."

        trades_df, metrics, _ = results
        return self._format_backtest_results(
            strategy="Buy-The-Dip", symbols=symbols, start_date=start_date,
            end_date=end_date, initial_capital=initial_capital,
            trades_df=trades_df, metrics=metrics,
            params={
                'Position Size': f"{position_size}%", 'Dip Threshold': f"{dip_threshold}%",
                'Hold Days': hold_days, 'Take Profit': f"{take_profit}%",
                'Stop Loss': f"{stop_loss}%", 'Interval': interval
            }
        )

    async def _run_momentum_backtest(self, symbols, start_date, end_date,
                                      initial_capital, position_size,
                                      lookback_period, momentum_threshold,
                                      hold_days, take_profit, stop_loss,
                                      interval, data_source) -> str:
        """Run momentum backtest and return markdown results."""
        from utils.backtester_util import backtest_momentum_strategy
        import pandas as pd

        results = backtest_momentum_strategy(
            symbols=symbols, start_date=start_date, end_date=end_date,
            initial_capital=initial_capital, position_size_pct=position_size,
            lookback_period=lookback_period, momentum_threshold=momentum_threshold,
            hold_days=hold_days, take_profit_pct=take_profit, stop_loss_pct=stop_loss,
            interval=interval, data_source=data_source,
            include_taf_fees=True, include_cat_fees=True
        )

        if results is not None:
            trades_df, _, _ = results
            output_dir = Path("backtest-results")
            output_dir.mkdir(exist_ok=True)
            from utils.tz_util import now_et
            timestamp = now_et().strftime("%Y%m%d_%H%M%S")
            filename = f"backtests_details_momentum_{timestamp}.csv"
            trades_df.to_csv(output_dir / filename, index=False)

        if results is None:
            return "# No Results\n\nNo trades were generated. Try adjusting parameters."

        trades_df, metrics, _ = results
        return self._format_backtest_results(
            strategy="Momentum", symbols=symbols, start_date=start_date,
            end_date=end_date, initial_capital=initial_capital,
            trades_df=trades_df, metrics=metrics,
            params={
                'Position Size': f"{position_size}%",
                'Lookback Period': f"{lookback_period} days",
                'Momentum Threshold': f"{momentum_threshold}%",
                'Hold Days': hold_days, 'Take Profit': f"{take_profit}%",
                'Stop Loss': f"{stop_loss}%", 'Interval': interval
            }
        )

    def _format_backtest_results(self, strategy, symbols, start_date, end_date,
                                  initial_capital, trades_df, metrics, params) -> str:
        """Format backtest results as markdown."""
        import pandas as pd

        md = f"# {strategy} Strategy Backtest Results\n\n"
        md += "## Configuration\n\n"
        md += f"- **Symbols**: {', '.join(symbols)}\n"
        from utils.tz_util import format_et
        md += f"- **Period**: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
        md += f"- **Initial Capital**: ${initial_capital:,.2f}\n"
        for key, value in params.items():
            md += f"- **{key}**: {value}\n"
        md += "\n"

        md += "## Performance Metrics\n\n"
        md += "| Metric | Value |\n|--------|-------|\n"
        md += f"| Total Return | {metrics['total_return']:.2f}% |\n"
        md += f"| Total P&L | ${metrics['total_pnl']:,.2f} |\n"
        md += f"| Annualized Return | {metrics['annualized_return']:.2f}% |\n"
        md += f"| Total Trades | {metrics['total_trades']} |\n"
        md += f"| Win Rate | {metrics['win_rate']:.1f}% |\n"
        md += f"| Max Drawdown | {metrics['max_drawdown']:.2f}% |\n"
        md += f"| Sharpe Ratio | {metrics['sharpe_ratio']:.2f} |\n\n"

        md += "## Recent Trades (Last 10)\n\n"
        recent_trades = trades_df.tail(10)
        md += "| Entry Time | Exit Time | Ticker | Shares | Entry $ | Exit $ | P&L | P&L % |\n"
        md += "|------------|-----------|--------|--------|---------|--------|-----|-------|\n"
        for _, trade in recent_trades.iterrows():
            entry_time = format_et(trade['entry_time'])
            exit_time = format_et(trade['exit_time'])
            md += (
                f"| {entry_time} | {exit_time} | {trade['ticker']} | {trade['shares']} | "
                f"${trade['entry_price']:.2f} | ${trade['exit_price']:.2f} | "
                f"${trade['pnl']:.2f} | {trade['pnl_pct']:.2f}% |\n"
            )

        final_capital = trades_df['capital_after'].iloc[-1]
        md += f"\n## Summary\n\n"
        md += (
            f"Starting with **${initial_capital:,.2f}**, the {strategy} strategy generated "
            f"**{metrics['total_trades']}** trades, resulting in a "
            f"**{metrics['total_return']:.2f}%** return (${metrics['total_pnl']:,.2f}). "
            f"Final portfolio value: **${final_capital:,.2f}**.\n"
        )

        return md
