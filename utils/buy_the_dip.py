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
                        dip_threshold: float = 0.02, hold_days: int = 1,
                        take_profit: float = 0.01, stop_loss: float = 0.005,
                        interval: str = '1d', data_source: str = 'yfinance',
                        include_taf_fees: bool = False, include_cat_fees: bool = False) -> Tuple[pd.DataFrame, Dict]:
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
    
    Returns:
        Tuple of (trades_df, metrics_dict)
    """
    
    # Import calculate_metrics from backtester_util
    from utils.backtester_util import calculate_metrics
    
    # Determine period based on interval
    if interval == '1d':
        period = '30d'
        lookback_periods = 20
    else:
        period = '30d'  # For intraday, use 30 days
        lookback_periods = 20  # 20 periods lookback
    
    # Fetch data based on source
    if data_source == 'yfinance' and interval != '1d':
        # Use intraday data from yfinance
        price_data = {}
        for symbol in symbols:
            df = get_intraday_data(symbol, interval=interval, period=period)
            if not df.empty:
                price_data[symbol] = df
    else:
        # Use daily data
        price_data = get_historical_data(symbols, start_date - timedelta(days=30), end_date)
    
    if not price_data:
        return None
    
    trades = []
    capital = initial_capital
    
    # Make start_date and end_date timezone-aware for intraday data
    if interval != '1d':
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=pytz.UTC)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=pytz.UTC)
    
    # Iterate through each trading day
    current_date = start_date
    while current_date <= end_date:
        
        for symbol in symbols:
            if symbol not in price_data:
                continue
            
            df = price_data[symbol]
            
            # Get data up to current date
            historical = df[df.index <= current_date]
            if len(historical) < lookback_periods:  # Need minimum history
                continue
            
            # Calculate recent high over lookback period
            recent_high = float(historical['High'].tail(lookback_periods).max())
            current_price = float(historical['Close'].iloc[-1])
            
            # Check if we have a dip
            dip_pct = (recent_high - current_price) / recent_high
            
            if dip_pct >= dip_threshold:
                # Enter trade
                entry_price = current_price
                entry_time = current_date
                shares = int((capital * position_size) / entry_price)
                
                if shares == 0:
                    continue
                
                # Calculate target and stop prices
                target_price = entry_price * (1 + take_profit)
                stop_price = entry_price * (1 - stop_loss)
                
                # Simulate holding period
                exit_time = entry_time + timedelta(days=hold_days)
                if exit_time > end_date:
                    exit_time = end_date
                
                # Get exit data
                future_data = df[(df.index > entry_time) & (df.index <= exit_time)]
                
                if future_data.empty:
                    continue
                
                # Check for take profit or stop loss
                hit_target = False
                hit_stop = False
                exit_price = None
                actual_exit_time = None
                
                for idx, row in future_data.iterrows():
                    if float(row['High']) >= target_price:
                        exit_price = target_price
                        actual_exit_time = idx
                        hit_target = True
                        break
                    elif float(row['Low']) <= stop_price:
                        exit_price = stop_price
                        actual_exit_time = idx
                        hit_stop = True
                        break
                
                # If neither hit, exit at end of hold period
                if exit_price is None:
                    exit_price = float(future_data['Close'].iloc[-1])
                    actual_exit_time = future_data.index[-1]
                
                # Calculate P&L
                pnl = (exit_price - entry_price) * shares
                
                # Calculate fees
                taf_fee = 0.0
                cat_fee_buy = 0.0
                cat_fee_sell = 0.0
                total_fees = 0.0
                
                # CAT fee on buy (entry)
                if include_cat_fees:
                    cat_fee_buy = calculate_cat_fee(shares)
                    total_fees += cat_fee_buy
                
                # TAF fee on sell (exit only)
                if include_taf_fees:
                    taf_fee = calculate_finra_taf_fee(shares)
                    total_fees += taf_fee
                
                # CAT fee on sell (exit)
                if include_cat_fees:
                    cat_fee_sell = calculate_cat_fee(shares)
                    total_fees += cat_fee_sell
                
                # Subtract all fees from P&L
                pnl -= total_fees
                
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                capital += pnl
                
                # Record trade
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': actual_exit_time,
                    'ticker': symbol,
                    'direction': 'long',
                    'shares': shares,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'target_price': target_price,
                    'stop_price': stop_price,
                    'hit_target': hit_target,
                    'hit_stop': hit_stop,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'capital_after': capital,
                    'dip_pct': dip_pct * 100,
                    'taf_fee': taf_fee,
                    'cat_fee': cat_fee_buy + cat_fee_sell,
                    'total_fees': total_fees
                })
        
        # Increment based on interval
        if interval == '1d':
            current_date += timedelta(days=1)
        elif interval == '60m':
            current_date += timedelta(hours=1)
        elif interval == '30m':
            current_date += timedelta(minutes=30)
        elif interval == '15m':
            current_date += timedelta(minutes=15)
        elif interval == '5m':
            current_date += timedelta(minutes=5)
    
    if not trades:
        return None
    
    # Create trades dataframe
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    metrics = calculate_metrics(trades_df, initial_capital, start_date, end_date)
    
    return trades_df, metrics
