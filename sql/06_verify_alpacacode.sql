-- Verification queries for the alpacacode schema

-- All runs
SELECT run_id, mode, strategy, status, started_at, completed_at
FROM alpacacode.runs;

-- Top backtest variations by Sharpe ratio
SELECT variation_index, total_return, total_pnl, win_rate,
       total_trades, sharpe_ratio, max_drawdown, is_best
FROM alpacacode.backtest_summaries
ORDER BY sharpe_ratio DESC LIMIT 5;

-- Sample trades
SELECT symbol, direction, shares, entry_price, exit_price,
       pnl, pnl_pct, hit_target, hit_stop, dip_pct, trade_type
FROM alpacacode.trades LIMIT 10;

-- Aggregate P&L by trade type
SELECT trade_type, count(*) AS num_trades,
       round(sum(pnl)::numeric, 2) AS total_pnl,
       round(avg(pnl_pct)::numeric, 4) AS avg_pnl_pct
FROM alpacacode.trades GROUP BY trade_type;

-- Validations
SELECT run_id, source, status, anomalies_found,
       anomalies_corrected, iterations_used
FROM alpacacode.validations;
