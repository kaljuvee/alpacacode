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

-- Legacy backtest summaries
SELECT run_id, timestamp, return_percent, total_trades,
       win_rate_percent, sharpe_ratio, strategy_id
FROM alpacacode.backtest_summary
ORDER BY timestamp DESC LIMIT 5;

-- Individual trades
SELECT ticker, direction, entry_price, exit_price, pnl, pnl_pct
FROM alpacacode.individual_trades
ORDER BY entry_time DESC LIMIT 10;

-- Strategies
SELECT strategy_id, strategy_name, strategy_type, is_active
FROM alpacacode.strategies;

-- Scheduled trades
SELECT job_id, strategy_id, schedule_type, is_active, next_run
FROM alpacacode.scheduled_trades;

-- All tables in the schema
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'alpacacode'
ORDER BY table_name;
