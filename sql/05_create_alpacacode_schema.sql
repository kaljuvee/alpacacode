-- AlpacaCode unified schema
-- All project tables consolidated under the alpacacode schema.

CREATE SCHEMA IF NOT EXISTS alpacacode;

-- Table 1: runs
-- Tracks each orchestrator run.
CREATE TABLE IF NOT EXISTS alpacacode.runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) UNIQUE NOT NULL,
    mode VARCHAR(32) NOT NULL,
    strategy VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    config JSONB,
    results JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_run_id ON alpacacode.runs(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON alpacacode.runs(status);

-- Table 2: backtest_summaries
-- One row per parameter variation tested in a backtest run.
CREATE TABLE IF NOT EXISTS alpacacode.backtest_summaries (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES alpacacode.runs(run_id),
    variation_index INTEGER NOT NULL DEFAULT 0,
    params JSONB,
    total_return NUMERIC(12,4),
    total_pnl NUMERIC(12,4),
    win_rate NUMERIC(8,4),
    total_trades INTEGER,
    sharpe_ratio NUMERIC(10,4),
    max_drawdown NUMERIC(10,4),
    annualized_return NUMERIC(10,4),
    is_best BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_summaries_run_id ON alpacacode.backtest_summaries(run_id);

-- Table 3: trades (unified)
-- Single table for backtest, paper, and live trades.
CREATE TABLE IF NOT EXISTS alpacacode.trades (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES alpacacode.runs(run_id),
    trade_type VARCHAR(16) NOT NULL,
    symbol VARCHAR(16),
    direction VARCHAR(8),
    shares NUMERIC(12,4),
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ,
    entry_price NUMERIC(12,4),
    exit_price NUMERIC(12,4),
    target_price NUMERIC(12,4),
    stop_price NUMERIC(12,4),
    hit_target BOOLEAN,
    hit_stop BOOLEAN,
    pnl NUMERIC(12,4),
    pnl_pct NUMERIC(10,4),
    capital_after NUMERIC(12,4),
    total_fees NUMERIC(10,4) DEFAULT 0,
    dip_pct NUMERIC(10,4),
    order_id VARCHAR(64),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_run_id ON alpacacode.trades(run_id);
CREATE INDEX IF NOT EXISTS idx_trades_trade_type ON alpacacode.trades(trade_type);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON alpacacode.trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_run_type ON alpacacode.trades(run_id, trade_type);

-- Table 4: validations
-- Stores validation run results.
CREATE TABLE IF NOT EXISTS alpacacode.validations (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES alpacacode.runs(run_id),
    source VARCHAR(16),
    status VARCHAR(16),
    total_checked INTEGER,
    anomalies_found INTEGER,
    anomalies_corrected INTEGER,
    iterations_used INTEGER,
    corrections JSONB,
    suggestions JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validations_run_id ON alpacacode.validations(run_id);

-- Table 5: backtest_summary (legacy)
-- Stores high-level metrics for each backtest run from the Streamlit UI.
CREATE TABLE IF NOT EXISTS alpacacode.backtest_summary (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_name VARCHAR(255) DEFAULT 'prediction_llm',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital NUMERIC(15, 2) NOT NULL,
    final_capital NUMERIC(15, 2) NOT NULL,
    total_pnl NUMERIC(15, 2) NOT NULL,
    return_percent NUMERIC(10, 4) NOT NULL,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    win_rate_percent NUMERIC(10, 4) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(10, 4) NOT NULL DEFAULT 0,
    sharpe_ratio NUMERIC(10, 4) NOT NULL DEFAULT 0,
    news_articles_used INTEGER NOT NULL DEFAULT 0,
    price_moves_used INTEGER NOT NULL DEFAULT 0,
    database_version VARCHAR(50) DEFAULT 'v1.0',
    agent VARCHAR(100) DEFAULT 'manus',
    annualized_return NUMERIC(10, 4) NOT NULL DEFAULT 0,
    rundate DATE NOT NULL,
    notes TEXT,
    strategy_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backtest_summary_run_id ON alpacacode.backtest_summary(run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_summary_timestamp ON alpacacode.backtest_summary(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_summary_strategy_id ON alpacacode.backtest_summary(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_summary_rundate ON alpacacode.backtest_summary(rundate DESC);

-- Table 6: individual_trades
-- Stores detailed information for each trade executed during backtests.
CREATE TABLE IF NOT EXISTS alpacacode.individual_trades (
    id SERIAL PRIMARY KEY,
    published_date TIMESTAMPTZ NOT NULL,
    market VARCHAR(50) DEFAULT 'US',
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('long', 'short')),
    shares INTEGER NOT NULL DEFAULT 1,
    entry_price NUMERIC(15, 4) NOT NULL,
    exit_price NUMERIC(15, 4) NOT NULL,
    target_price NUMERIC(15, 4) DEFAULT 0,
    stop_price NUMERIC(15, 4) DEFAULT 0,
    hit_target BOOLEAN DEFAULT FALSE,
    hit_stop BOOLEAN DEFAULT FALSE,
    pnl NUMERIC(15, 2) NOT NULL DEFAULT 0,
    pnl_pct NUMERIC(10, 4) NOT NULL DEFAULT 0,
    capital_after NUMERIC(15, 2) NOT NULL DEFAULT 0,
    news_event VARCHAR(255),
    link TEXT,
    runid VARCHAR(255) NOT NULL,
    rundate TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    news_id INTEGER,
    agent VARCHAR(100) DEFAULT 'manus'
);

CREATE INDEX IF NOT EXISTS idx_individual_trades_runid ON alpacacode.individual_trades(runid);
CREATE INDEX IF NOT EXISTS idx_individual_trades_ticker ON alpacacode.individual_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_individual_trades_entry_time ON alpacacode.individual_trades(entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_individual_trades_rundate ON alpacacode.individual_trades(rundate DESC);

-- Table 7: strategies
-- Stores strategy definitions and configurations.
CREATE TABLE IF NOT EXISTS alpacacode.strategies (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(255) UNIQUE NOT NULL,
    strategy_name VARCHAR(255) NOT NULL,
    strategy_type VARCHAR(100) NOT NULL,
    description TEXT,
    parameters JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_strategies_strategy_id ON alpacacode.strategies(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategies_strategy_type ON alpacacode.strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_strategies_is_active ON alpacacode.strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_strategies_created_at ON alpacacode.strategies(created_at DESC);

-- Insert default strategies
INSERT INTO alpacacode.strategies (strategy_id, strategy_name, strategy_type, description, parameters)
VALUES
    ('buy-the-dip', 'Buy The Dip', 'momentum', 'Buy stocks when they dip below a certain threshold',
     '{"dip_threshold": 0.02, "hold_period_days": 1}'::jsonb),
    ('vix-fear', 'VIX Fear Index', 'volatility', 'Buy when VIX exceeds threshold indicating high fear',
     '{"vix_threshold": 20, "hold_overnight": true}'::jsonb)
ON CONFLICT (strategy_id) DO NOTHING;

-- Table 8: scheduled_trades
-- Stores scheduled trading jobs and their execution status.
CREATE TABLE IF NOT EXISTS alpacacode.scheduled_trades (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    strategy_id VARCHAR(255) NOT NULL,
    schedule_type VARCHAR(50) NOT NULL CHECK (schedule_type IN ('once', 'daily', 'weekly', 'cron')),
    schedule_expression VARCHAR(255),
    start_time TIME,
    end_time TIME,
    is_paper BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    run_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_scheduled_trades_job_id ON alpacacode.scheduled_trades(job_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_trades_strategy_id ON alpacacode.scheduled_trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_trades_is_active ON alpacacode.scheduled_trades(is_active);
CREATE INDEX IF NOT EXISTS idx_scheduled_trades_next_run ON alpacacode.scheduled_trades(next_run);
