# AlpacaCode

Trading strategy simulator, backtester, and paper trader.

## Stack

- **Python 3.13**, virtualenv at `.venv/`
- **Streamlit** web UI (`Home.py`, `pages/`)
- **Textual** TUI (`tui/app.py`)
- **CLI** paper trader (`tasks/cli_trader.py`)
- **Config**: `config/parameters.yaml` (strategy params), `.env` (API keys)

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `pages/` | Streamlit pages (VIX, AI Assistant, Alpaca Trader, Alpaca Chat, Futures, Methodology) |
| `utils/` | Core logic (alpaca_util, buy_the_dip, vix_strategy, momentum, massive_util, backtester_util, backtest_db_util) |
| `utils/db/` | Database pool (`db_pool.py`) |
| `tasks/` | CLI tools (cli_trader.py, validate_backtest.py) |
| `tui/` | Textual TUI app |
| `agents/` | Multi-agent system (backtester, paper-trader, validator, orchestrator) |
| `agents/shared/` | Message bus, shared state, DB setup |
| `tests/` | Tests |
| `data/` | Runtime data (orders, agent messages, agent state) |
| `config/` | parameters.yaml |

## Strategies

- **Buy the Dip**: Buys on `dip_threshold%` drops from recent high, exits at `take_profit_threshold%` gain, `stop_loss_threshold%` loss, or after `hold_days`
- **VIX Fear Index**: Trades based on VIX levels exceeding threshold
- **Momentum**: Buys on strong upward momentum over lookback period
- **Box-Wedge**: Pattern-based strategy

## Required Environment Variables (.env)

```
ALPACA_PAPER_API_KEY=...
ALPACA_PAPER_SECRET_KEY=...
MASSIVE_API_KEY=...        # Polygon.io compatible
EODHD_API_KEY=...
XAI_API_KEY=...
DATABASE_URL=...           # PostgreSQL connection string
```

## Multi-Agent System

Four agents collaborate to backtest, paper trade, and validate strategies:

### Agent 1: Backtester (`agents/backtest_agent.py`)
- Runs parameterized backtests varying symbols, date ranges, and strategy parameters
- Stores results via `backtest_db_util.py` into `backtest_summary` / `individual_trades` tables
- Reports best-performing configuration to Portfolio Manager

### Agent 2: Paper Trader (`agents/paper_trade_agent.py`)
- Continuous paper trading via real Alpaca paper API
- Polls at configurable intervals, tracks positions and daily P&L
- Writes trades to `trades` DB table

### Agent 3: Validator (`agents/validate_agent.py`)
- Cross-checks trades against Massive market data for price accuracy
- Validates P&L math, market hours, weekend trades, TP/SL logic
- **Self-correction loop**: Attempts up to `n=10` iterations to fix anomalies
- After 10 failed iterations: stops, reports error behaviors, suggests fixes

### Agent 4: Portfolio Manager (`agents/orchestrator.py`)
- Orchestrator — dispatches work, tracks state, routes messages
- Workflow: Backtest -> Validate -> Paper Trade -> Validate -> Report

### Communication
- File-based JSON message bus (`data/agent_messages/`)
- Messages: `{from_agent, to_agent, type, payload, timestamp}`
- State persistence: `data/agent_state.json`

### Running

```bash
# Full cycle: backtest -> validate -> paper trade -> validate
python agents/orchestrator.py --mode full

# Backtest only
python agents/orchestrator.py --mode backtest

# Validate a specific run
python agents/orchestrator.py --mode validate --run-id <uuid>

# Paper trade only (short test)
python agents/orchestrator.py --mode paper --duration 1h
```
