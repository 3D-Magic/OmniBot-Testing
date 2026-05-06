
"""
Yahoo Finance data client - free backup for Alpaca historical bars
"""
import logging
import time
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class YFinanceDataClient:
    """Free data source using yfinance - no API key required"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 60  # seconds
    
    def get_bars(self, symbol: str, interval: str = '5m', limit: int = 30):
        """Get historical bars from Yahoo Finance"""
        cache_key = f"{symbol}:{interval}:{limit}"
        now = time.time()
        if cache_key in self._cache and now - self._cache_time.get(cache_key, 0) < self._cache_ttl:
            return self._cache[cache_key]
        
        try:
            import yfinance as yf
            
            # Map interval to yfinance period
            # yfinance needs a period string for intraday data
            if interval in ('1m', '2m', '5m', '15m', '30m', '60m', '90m'):
                period = '5d' if limit <= 78 else '1mo'
            else:
                period = '1mo'
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df is not None and len(df) > 0:
                # Take last N bars
                df = df.tail(limit).copy()
                # Rename columns to match Alpaca format
                df.columns = [c.lower().replace(' ', '_') for c in df.columns]
                if 'adj_close' in df.columns:
                    df = df.drop(columns=['adj_close'])
                if 'dividends' in df.columns:
                    df = df.drop(columns=['dividends'])
                if 'stock_splits' in df.columns:
                    df = df.drop(columns=['stock_splits'])
                
                # Ensure standard column names
                col_map = {'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'}
                for old, new in col_map.items():
                    if old in df.columns and old != new:
                        df = df.rename(columns={old: new})
                
                self._cache[cache_key] = df
                self._cache_time[cache_key] = now
                logger.info(f"[YFINANCE] Fetched {len(df)} bars for {symbol}")
                return df
            else:
                logger.warning(f"[YFINANCE] No data for {symbol}")
                return None
                
        except ImportError:
            logger.warning("[YFINANCE] yfinance not installed. Run: pip install yfinance")
            return None
        except Exception as e:
            logger.warning(f"[YFINANCE] Error fetching {symbol}: {e}")
            return None

# Global instance
_yf_client = None

def get_yf_client():
    global _yf_client
    if _yf_client is None:
        _yf_client = YFinanceDataClient()
    return _yf_client
