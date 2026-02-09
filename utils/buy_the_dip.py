"""
Buy-The-Dip Trading Strategy
Buys when stock drops by threshold from recent high, holds for specified days or until take profit/stop loss
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import yfinance as yf
import pytz
from utils.polygon_util import is_market_open


def get_intraday_data(ticker: str, interval: str = '1d', period: str = '30d') -> pd.DataFrame:
    """
    Fetch intraday or daily data from yfinance
    
    Args:
        ticker: Stock symbol
        interval: Data interval ('1d', '60m', '30m', '15m', '5m')
        period: Time period ('30d', '7d', '1d')
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            print(f"Warning: No data returned for {ticker} with interval {interval}")
            return pd.DataFrame()
        
        # Ensure timezone-aware datetime index
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {str(e)}")
        return pd.DataFrame()


def get_historical_data(symbols: List[str], start_date: datetime, 
                       end_date: datetime) -> Dict[str, pd.DataFrame]:
    """Fetch historical price data for multiple symbols"""
    data = {}
    for symbol in symbols:
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not df.empty:
                data[symbol] = df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    return data


def calculate_finra_taf_fee(shares: int) -> float:
    """
    Calculate FINRA Trading Activity Fee (TAF) for a sell order
    
    TAF: $0.000166 per share (sells only)
    - Rounded up to nearest penny
    - Capped at $8.30 per trade
    
    Args:
        shares: Number of shares being sold
    
    Returns:
        Fee amount in dollars
    """
    if shares <= 0:
        return 0.0
    
    fee_per_share = 0.000166
    raw_fee = shares * fee_per_share
    
    # Round up to nearest penny
    fee = np.ceil(raw_fee * 100) / 100
    
    # Cap at $8.30
    fee = min(fee, 8.30)
    
    return fee


def calculate_cat_fee(shares: int) -> float:
    """
    Calculate Consolidated Audit Trail (CAT) fee for a trade
    
    CAT Fee: $0.0000265 per share (applies to both buys and sells)
    - For NMS Equities: 1:1 ratio
    - For OTC Equities: 1:0.01 ratio (we assume NMS for regular stocks)
    - No cap mentioned
    
    Args:
        shares: Number of shares being traded
    
    Returns:
        Fee amount in dollars
    """
    if shares <= 0:
        return 0.0
    
    # CAT Fee Rate for NMS Equities: $0.0000265 per share
    fee_per_share = 0.0000265
    fee = shares * fee_per_share
    
    return fee


def backtest_buy_the_dip(symbols: List[str], start_date: datetime, end_date: datetime,
                        initial_capital: float = 10000, position_size: float = 0.1,
                        dip_threshold: float = 0.02, hold_days: int = 2,
                        take_profit: float = 0.01, stop_loss: float = 0.005,
                        interval: str = '1d', data_source: str = 'polygon',
                        include_taf_fees: bool = False, include_cat_fees: bool = False,
                        pdt_protection: Optional[bool] = None) -> Tuple[pd.DataFrame, Dict]:
    """
    Backtest buy-the-dip strategy
    
    Strategy: Buy when stock drops by dip_threshold from recent high, 
              hold for hold_days or until take_profit/stop_loss hit
    
    Args:
        symbols: List of stock symbols to trade
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Starting capital
        position_size: Fraction of capital to use per trade
        dip_threshold: Percentage drop to trigger buy (e.g., 0.02 = 2%)
        hold_days: Days/periods to hold position
        take_profit: Take profit percentage (e.g., 0.01 = 1%)
        stop_loss: Stop loss percentage (e.g., 0.005 = 0.5%)
        interval: Data interval ('1d', '60m', '30m', '15m', '5m')
        data_source: Data source ('yfinance' or 'polygon')
        include_taf_fees: Include FINRA TAF fees
        include_cat_fees: Include Consolidated Audit Trail fees
        pdt_protection: If True, prevents same-day exits. Defaults to True if initial_capital < $25k.
    
    Returns:
        Tuple of (trades_df, metrics_dict, equity_df)
    """
    
    # Import calculate_metrics from backtester_util
    from utils.backtester_util import calculate_metrics
    
    # Set PDT status
    if pdt_protection is None:
        pdt_active = initial_capital < 25000
    else:
        pdt_active = pdt_protection
    
    # Determine lookback_periods based on interval
    # We want approx 20 trading days of lookback
    if interval == '1d':
        lookback_periods = 20
        period = '40d' # Fetch enough data for lookback
    else:
        # For intraday, we need many more bars to cover 20 trading days
        # E.g., for 60m data, there are 16 bars per day (4am-8pm)
        # 20 days * 16 bars = 320 periods
        bars_per_day = 16 if interval == '60m' else 192 if interval == '5m' else 960 if interval == '1m' else 20
        lookback_periods = 20 * bars_per_day
        period = '60d'
    
    # Fetch data based on source
    if data_source == 'polygon' or (data_source == 'yfinance' and interval != '1d'):
        # Use intraday data
        price_data = {}
        for symbol in symbols:
            df = get_intraday_data(symbol, interval=interval, period=period)
            if not df.empty:
                price_data[symbol] = df
    else:
        # Use daily data
        price_data = get_historical_data(symbols, start_date - timedelta(days=40), end_date)
    
    if not price_data:
        return None
    
    trades = []
    available_capital = initial_capital
    active_trades = {} # ticker: trade_info
    
    # Standardize timezones
    is_aware = False
    for symbol in symbols:
        if symbol in price_data and not price_data[symbol].empty:
            if price_data[symbol].index.tz is not None:
                is_aware = True
                break
    
    if is_aware:
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=pytz.UTC)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=pytz.UTC)
    else:
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
    
    # Get all unique timestamps from the data within range
    all_timestamps = set()
    for df in price_data.values():
        all_timestamps.update(df.index)
    
    sorted_timestamps = sorted([t for t in all_timestamps if start_date <= t <= end_date])
    
    equity_curve = []
    
    for current_date in sorted_timestamps:
        # Adjust time for daily data reporting
        display_time = current_date
        if interval == '1d':
            eastern = pytz.timezone('US/Eastern')
            if display_time.tzinfo is None:
                display_time = pytz.utc.localize(display_time).astimezone(eastern)
            else:
                display_time = display_time.astimezone(eastern)
            display_time = display_time.replace(hour=9, minute=30)
        
        # 1. PROCESS EXITS FIRST (Chronological order)
        closed_this_tick = []
        for symbol, trade in active_trades.items():
            df = price_data[symbol]
            current_bar = df.loc[current_date]
            
            # Use same reporting shift for exit time
            exit_display_time = current_date
            if interval == '1d':
                eastern = pytz.timezone('US/Eastern')
                if exit_display_time.tzinfo is None:
                    exit_display_time = pytz.utc.localize(exit_display_time).astimezone(eastern)
                else:
                    exit_display_time = exit_display_time.astimezone(eastern)
                exit_display_time = exit_display_time.replace(hour=16, minute=0)

            # PDT Check: Cannot exit on same calendar day as entry if PDT active
            # Note: current_date and trade['entry_date_raw'] are in UTC/data timezone
            is_same_day = current_date.date() == trade['entry_date_raw']
            can_day_trade = not (pdt_active and is_same_day)

            hit_tp = can_day_trade and float(current_bar['High']) >= trade['target_price']
            hit_sl = can_day_trade and float(current_bar['Low']) <= trade['stop_price']
            hit_end = current_date >= trade['max_exit_time']
            
            if hit_tp or hit_sl or hit_end:
                exit_price = trade['target_price'] if hit_tp else trade['stop_price'] if hit_sl else float(current_bar['Close'])
                
                # Calculate P&L and fees
                pnl = (exit_price - trade['entry_price']) * trade['shares']
                
                taf_fee = calculate_finra_taf_fee(trade['shares']) if include_taf_fees else 0.0
                cat_fee_buy = calculate_cat_fee(trade['shares']) if include_cat_fees else 0.0
                cat_fee_sell = calculate_cat_fee(trade['shares']) if include_cat_fees else 0.0
                total_fees = taf_fee + cat_fee_buy + cat_fee_sell
                
                pnl -= total_fees
                available_capital += (trade['entry_price'] * trade['shares']) + pnl
                pnl_pct = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
                
                # Calculate total equity (Cash + Market Value of REMAINING positions)
                total_market_value = 0
                for open_symbol, open_trade in active_trades.items():
                    if open_symbol == symbol: continue # This one just closed
                    try:
                        cur_p = float(price_data[open_symbol].loc[current_date, 'Close'])
                    except KeyError:
                        cur_p = float(price_data[open_symbol][:current_date]['Close'].iloc[-1])
                    total_market_value += open_trade['shares'] * cur_p
                
                total_equity = available_capital + total_market_value
                
                trades.append({
                    'entry_time': trade['entry_time'],
                    'exit_time': exit_display_time,
                    'ticker': symbol,
                    'direction': 'long',
                    'shares': trade['shares'],
                    'entry_price': trade['entry_price'],
                    'exit_price': exit_price,
                    'target_price': trade['target_price'],
                    'stop_price': trade['stop_price'],
                    'hit_target': hit_tp,
                    'hit_stop': hit_sl and not hit_tp,
                    'TP': 1 if hit_tp else 0,
                    'SL': 1 if hit_sl and not hit_tp else 0,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'capital_after': total_equity,
                    'dip_pct': trade['dip_pct'] * 100,
                    'taf_fee': taf_fee,
                    'cat_fee': cat_fee_buy + cat_fee_sell,
                    'total_fees': total_fees
                })
                closed_this_tick.append(symbol)
        
        for symbol in closed_this_tick:
            del active_trades[symbol]

        # 2. PROCESS ENTRIES
        if not is_market_open(display_time):
            continue

        for symbol in symbols:
            if symbol not in price_data or symbol in active_trades:
                continue
            
            df = price_data[symbol]
            historical = df[df.index <= current_date]
            if len(historical) < lookback_periods:
                continue
            
            recent_high = float(historical['High'].tail(lookback_periods).max())
            current_price = float(historical['Close'].iloc[-1])
            dip_pct = (recent_high - current_price) / recent_high
            
            if dip_pct >= dip_threshold:
                # Enter trade
                shares = int((available_capital * position_size) / current_price)
                if shares <= 0:
                    continue
                
                # Check for enough capital
                cost = current_price * shares
                if cost > available_capital:
                    shares = int(available_capital / current_price)
                    cost = current_price * shares
                    if shares <= 0: continue
                
                available_capital -= cost
                
                active_trades[symbol] = {
                    'entry_time': display_time,
                    'entry_date_raw': current_date.date(),
                    'entry_price': current_price,
                    'shares': shares,
                    'target_price': current_price * (1 + take_profit),
                    'stop_price': current_price * (1 - stop_loss),
                    'max_exit_time': current_date + timedelta(days=hold_days),
                    'dip_pct': dip_pct
                }
        
        # 3. RECORD EQUITY AT END OF TICK
        total_open_value = 0
        for open_symbol, open_trade in active_trades.items():
            try:
                cur_p = float(price_data[open_symbol].loc[current_date, 'Close'])
            except KeyError:
                cur_p = float(price_data[open_symbol][:current_date]['Close'].iloc[-1])
            total_open_value += open_trade['shares'] * cur_p
        
        tick_equity = available_capital + total_open_value
        equity_curve.append({
            'timestamp': display_time,
            'equity': tick_equity
        })
    
    if not trades:
        return None
    
    trades_df = pd.DataFrame(trades).sort_values('exit_time')
    equity_df = pd.DataFrame(equity_curve)
    
    # Calculate metrics using equity curve for drawdown for better accuracy
    metrics = calculate_metrics(trades_df, initial_capital, start_date, end_date)
    
    # Override drawdown and annualized return if we have equity_df
    if not equity_df.empty:
        # Annualized return from equity curve
        final_equity = equity_df['equity'].iloc[-1]
        days = (end_date - start_date).days
        years = days / 365.25
        if years > 0:
            metrics['annualized_return'] = ((final_equity / initial_capital) ** (1 / years) - 1) * 100
        
        # Max drawdown from equity curve
        ec = equity_df['equity'].values
        running_max = np.maximum.accumulate(ec)
        drawdown = (ec - running_max) / running_max
        metrics['max_drawdown'] = abs(drawdown.min()) * 100
        
    return trades_df, metrics, equity_df
