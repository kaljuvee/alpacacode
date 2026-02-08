#!/usr/bin/env python3
"""
Polygon API Utility

Provides access to Polygon.io API for intraday price data with fallback to yfinance.
Requires POLYGON_API_KEY environment variable to be set.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import pytz
from typing import Optional, Dict, Any
import logging
logger = logging.getLogger(__name__)

class PolygonUtil:
    """Utility class for accessing Polygon.io API with yfinance fallback"""
    
    def __init__(self):
        """Initialize Polygon utility"""
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.base_url = "https://api.polygon.io"
        self.use_polygon = bool(self.api_key)
        
        if self.use_polygon:
            logger.info("Polygon API key found, will use Polygon.io for price data")
        else:
            logger.info("No Polygon API key found, will use yfinance for price data")
    
    def get_intraday_prices(self, symbol: str, date: datetime, interval: str = '5') -> pd.DataFrame:
        """
        Get intraday price data for a specific date
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            date: Date to get data for
            interval: Time interval in minutes (default: '5' for 5-minute bars)
        
        Returns:
            DataFrame with OHLCV data
        """
        if self.use_polygon:
            return self._get_polygon_intraday(symbol, date, interval)
        else:
            return self._get_yfinance_intraday(symbol, date, interval)
    
    def _get_polygon_intraday(self, symbol: str, date: datetime, interval: str) -> pd.DataFrame:
        """Get intraday data from Polygon.io API"""
        try:
            # Format date for Polygon API
            date_str = date.strftime('%Y-%m-%d')
            
            # Polygon API endpoint for intraday data
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{interval}/minute/{date_str}/{date_str}"
            
            params = {
                'apiKey': self.api_key,
                'adjusted': 'true',
                'sort': 'asc'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'OK' or data['resultsCount'] == 0:
                logger.warning(f"No Polygon data available for {symbol} on {date_str}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data['results'])
            
            # Rename columns to match yfinance format
            df = df.rename(columns={
                'o': 'Open',
                'h': 'High', 
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume',
                't': 'timestamp'
            })
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Select only OHLCV columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            logger.info(f"Retrieved {len(df)} bars from Polygon for {symbol} on {date_str}")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Polygon API request failed for {symbol}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error getting Polygon data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _get_yfinance_intraday(self, symbol: str, date: datetime, interval: str) -> pd.DataFrame:
        """Get intraday data from yfinance (fallback)"""
        try:
            start_date = date.strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Convert interval to yfinance format
            yf_interval = f"{interval}m"
            
            data = yf.download(symbol, start=start_date, end=end_date, interval=yf_interval, progress=False)
            
            if data.empty:
                logger.warning(f"No yfinance data available for {symbol} on {start_date}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting yfinance data for {symbol}: {e}")
            return pd.DataFrame()
            
    def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str = 'day', interval: int = 1) -> pd.DataFrame:
        """
        Get historical price data for a range of dates
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            timeframe: 'minute', 'hour', 'day', 'week', 'month', 'quarter', 'year'
            interval: Number of timeframes per bar
            
        Returns:
            DataFrame with OHLCV data
        """
        if self.use_polygon:
            return self._get_polygon_historical(symbol, start_date, end_date, timeframe, interval)
        else:
            return self._get_yfinance_historical(symbol, start_date, end_date, timeframe, interval)

    def _get_polygon_historical(self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str, interval: int) -> pd.DataFrame:
        """Get historical data from Polygon.io API across a range"""
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{interval}/{timeframe}/{start_str}/{end_str}"
            params = {
                'apiKey': self.api_key,
                'adjusted': 'true',
                'sort': 'asc'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] != 'OK' or data.get('resultsCount', 0) == 0:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['results'])
            df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume', 't': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            logger.error(f"Error getting Polygon historical for {symbol}: {e}")
            return pd.DataFrame()

    def _get_yfinance_historical(self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str, interval: int) -> pd.DataFrame:
        """Get historical data from yfinance fallback"""
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            yf_interval = '1d'
            if timeframe == 'minute':
                yf_interval = f'{interval}m'
            elif timeframe == 'hour':
                yf_interval = f'{interval}h'
            elif timeframe == 'day':
                yf_interval = f'{interval}d'
            
            data = yf.download(symbol, start=start_str, end=end_str, interval=yf_interval, progress=False)
            return data
        except Exception as e:
            logger.error(f"Error getting yfinance historical for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get basic ticker information
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with ticker info or None if not found
        """
        if self.use_polygon:
            return self._get_polygon_ticker_info(symbol)
        else:
            return self._get_yfinance_ticker_info(symbol)
    
    def _get_polygon_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker info from Polygon API"""
        try:
            url = f"{self.base_url}/v3/reference/tickers/{symbol}"
            params = {'apiKey': self.api_key}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK':
                return {
                    'symbol': data['results']['ticker'],
                    'name': data['results']['name'],
                    'market': data['results']['market'],
                    'locale': data['results']['locale'],
                    'primary_exchange': data['results']['primary_exchange'],
                    'type': data['results']['type'],
                    'active': data['results']['active']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Polygon ticker info for {symbol}: {e}")
            return None
    
    def _get_yfinance_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker info from yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'market': info.get('market', ''),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting yfinance ticker info for {symbol}: {e}")
            return None
    
    def is_market_open(self, date: datetime) -> bool:
        """
        Check if market is open on given date
        
        Args:
            date: Date to check
        
        Returns:
            True if market is open, False otherwise
        """
        if self.use_polygon:
            return self._check_polygon_market_status(date)
        else:
            return self._check_yfinance_market_status(date)
    
    def _check_polygon_market_status(self, date: datetime) -> bool:
        """Check market status using Polygon API"""
        try:
            # Convert to US/Eastern
            eastern = pytz.timezone('US/Eastern')
            if date.tzinfo is not None:
                date_et = date.astimezone(eastern)
            else:
                date_et = pytz.utc.localize(date).astimezone(eastern)
            
            hour = date_et.hour
            if date_et.weekday() < 5:  # Weekday
                return 4 <= hour < 20
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking Polygon market status: {e}")
            return False
    
    def _check_yfinance_market_status(self, date: datetime) -> bool:
        """Check market status using yfinance"""
        try:
            # Convert to US/Eastern
            eastern = pytz.timezone('US/Eastern')
            if date.tzinfo is not None:
                date_et = date.astimezone(eastern)
            else:
                date_et = pytz.utc.localize(date).astimezone(eastern)
                
            hour = date_et.hour
            return date_et.weekday() < 5 and 4 <= hour < 20
            
        except Exception as e:
            logger.error(f"Error checking yfinance market status: {e}")
            return False

# Global instance
polygon_util = PolygonUtil()

# Convenience functions
def get_intraday_prices(symbol: str, date: datetime, interval: str = '5') -> pd.DataFrame:
    """Get intraday price data with automatic fallback"""
    return polygon_util.get_intraday_prices(symbol, date, interval)

def get_ticker_info(symbol: str) -> Optional[Dict[str, Any]]:
    """Get ticker information with automatic fallback"""
    return polygon_util.get_ticker_info(symbol)

def is_market_open(date: datetime) -> bool:
    """Check if market is open with automatic fallback"""
    return polygon_util.is_market_open(date)

def get_historical_data(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = 'day', interval: int = 1) -> pd.DataFrame:
    """Get historical price data with automatic fallback"""
    return polygon_util.get_historical_data(symbol, start_date, end_date, timeframe, interval)
