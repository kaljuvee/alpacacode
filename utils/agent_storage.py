"""
Agent Storage Utility

Provides configurable storage backends (file or DB) for agent results.
Controlled by `general.storage_backend` in config/parameters.yaml.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CONFIG_PATH = PROJECT_ROOT / "config" / "parameters.yaml"
DATA_DIR = PROJECT_ROOT / "data"
BACKTEST_DIR = DATA_DIR / "backtest_results"
PAPER_TRADE_DIR = DATA_DIR / "paper_trades"


def get_storage_backend() -> str:
    """Read storage_backend from config. Defaults to 'file'."""
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        return cfg.get("general", {}).get("storage_backend", "file")
    except Exception:
        return "file"


# ---------------------------------------------------------------------------
# Backtest results
# ---------------------------------------------------------------------------

def store_backtest_results(run_id: str, best: Dict, all_results: List[Dict],
                           trades: Optional[List[Dict]] = None):
    """Store backtest results using the configured backend."""
    backend = get_storage_backend()
    if backend == "db":
        _store_backtest_db(run_id, best, all_results)
    else:
        _store_backtest_file(run_id, best, all_results, trades)


def _store_backtest_file(run_id: str, best: Dict, all_results: List[Dict],
                         trades: Optional[List[Dict]] = None):
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKTEST_DIR / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "best_config": best,
        "all_results": all_results,
        "trades": trades or [],
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    logger.info(f"Backtest results written to {path}")


def _store_backtest_db(run_id: str, best: Dict, all_results: List[Dict]):
    from utils.backtest_db_util import BacktestDatabaseUtil

    db = BacktestDatabaseUtil()
    params = best.get("params", {})
    db.store_backtest_summary({
        "run_id": run_id,
        "model_name": "backtest_agent",
        "start_date": str(datetime.now().date() - timedelta(days=90)),
        "end_date": str(datetime.now().date()),
        "initial_capital": 10000,
        "final_capital": 10000 + best.get("total_pnl", 0),
        "total_pnl": best.get("total_pnl", 0),
        "return_percent": best.get("total_return", 0),
        "total_trades": best.get("total_trades", 0),
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate_percent": best.get("win_rate", 0),
        "max_drawdown": best.get("max_drawdown", 0),
        "sharpe_ratio": best.get("sharpe_ratio", 0),
        "annualized_return": best.get("annualized_return", 0),
        "agent": "backtest_agent",
        "notes": f"Grid search: {len(all_results)} variations. Best params: {params}",
    })
    logger.info(f"Backtest results stored to DB for run {run_id}")


def fetch_backtest_trades(run_id: str) -> List[Dict]:
    """Fetch backtest trades using the configured backend."""
    backend = get_storage_backend()
    if backend == "db":
        return _fetch_backtest_trades_db(run_id)
    return _fetch_backtest_trades_file(run_id)


def _fetch_backtest_trades_file(run_id: str) -> List[Dict]:
    path = BACKTEST_DIR / f"{run_id}.json"
    if not path.exists():
        logger.warning(f"Backtest file not found: {path}")
        return []
    data = json.loads(path.read_text())
    return data.get("trades", [])


def _fetch_backtest_trades_db(run_id: str) -> List[Dict]:
    from utils.backtest_db_util import get_individual_trades
    return get_individual_trades(run_id)


# ---------------------------------------------------------------------------
# Paper trades
# ---------------------------------------------------------------------------

def store_paper_trade(session_id: str, trade: Dict):
    """Store a single paper trade using the configured backend."""
    backend = get_storage_backend()
    if backend == "db":
        _store_paper_trade_db(session_id, trade)
    else:
        _store_paper_trade_file(session_id, trade)


def _store_paper_trade_file(session_id: str, trade: Dict):
    PAPER_TRADE_DIR.mkdir(parents=True, exist_ok=True)
    path = PAPER_TRADE_DIR / f"{session_id}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(trade, default=str) + "\n")
    logger.debug(f"Paper trade appended to {path}")


def _store_paper_trade_db(session_id: str, trade: Dict):
    from utils.db.db_pool import DatabasePool
    from sqlalchemy import text

    pool = DatabasePool()
    with pool.get_session() as session:
        session.execute(
            text("""
                INSERT INTO trades (run_id, session_id, agent, symbol, side, qty,
                                    price, filled_price, order_id, status, pnl,
                                    pnl_pct, strategy, notes)
                VALUES (:run_id, :session_id, :agent, :symbol, :side, :qty,
                        :price, :filled_price, :order_id, :status, :pnl,
                        :pnl_pct, :strategy, :notes)
            """),
            {
                "run_id": session_id,
                "session_id": session_id,
                "agent": "paper_trader",
                "symbol": trade.get("symbol"),
                "side": trade.get("side"),
                "qty": trade.get("qty", 0),
                "price": trade.get("price") or trade.get("entry_price"),
                "filled_price": trade.get("exit_price"),
                "order_id": trade.get("order_id"),
                "status": "filled",
                "pnl": trade.get("pnl"),
                "pnl_pct": trade.get("pnl_pct"),
                "strategy": "buy_the_dip",
                "notes": trade.get("reason", ""),
            },
        )
    logger.debug(f"Paper trade stored to DB for session {session_id}")


def fetch_paper_trades(run_id: str) -> List[Dict]:
    """Fetch paper trades using the configured backend."""
    backend = get_storage_backend()
    if backend == "db":
        return _fetch_paper_trades_db(run_id)
    return _fetch_paper_trades_file(run_id)


def _fetch_paper_trades_file(run_id: str) -> List[Dict]:
    path = PAPER_TRADE_DIR / f"{run_id}.jsonl"
    if not path.exists():
        logger.warning(f"Paper trades file not found: {path}")
        return []
    trades = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            trades.append(json.loads(line))
    return trades


def _fetch_paper_trades_db(run_id: str) -> List[Dict]:
    from utils.db.db_pool import DatabasePool
    from sqlalchemy import text

    pool = DatabasePool()
    with pool.get_session() as session:
        result = session.execute(
            text("SELECT * FROM trades WHERE run_id = :run_id ORDER BY timestamp"),
            {"run_id": run_id},
        )
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
