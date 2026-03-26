"""
OMNIBOT v2.7 Titan - Data Fetcher
Unified market data aggregation
"""

import logging
import yfinance as yf
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Unified data fetcher for all markets
    Falls back between data sources
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.primary_source = config.get('primary', 'yfinance')
        self.fallback_source = config.get('fallback', 'ccxt')
        self.cache_enabled = config.get('cache_enabled', True)
        self.cache = {}
    
    def get_stock_data(self, symbol: str, period: str = "1d") -> Optional[Dict]:
        """Fetch stock data from yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
            
            latest = hist.iloc[-1]
            return {
                'symbol': symbol,
                'price': float(latest['Close']),
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'change': float(latest['Close'] - hist.iloc[-2]['Close']) if len(hist) > 1 else 0,
                'timestamp': hist.index[-1].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    def get_multiple_stocks(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch data for multiple stocks"""
        data = {}
        for symbol in symbols:
            result = self.get_stock_data(symbol)
            if result:
                data[symbol] = result
        return data
    
    def get_crypto_data(self, symbol: str, exchange=None) -> Optional[Dict]:
        """Fetch crypto data (placeholder for CCXT integration)"""
        # This would integrate with crypto_engine
        pass
    
    def get_forex_data(self, pair: str) -> Optional[Dict]:
        """Fetch forex data (placeholder for OANDA integration)"""
        # This would integrate with forex_engine
        pass
    
    def clear_cache(self):
        """Clear data cache"""
        self.cache.clear()