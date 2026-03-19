"""
OMNIBOT v2.6 Sentinel - Data Fetcher
Fetches market data from free sources
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from config.settings import API, CACHE_DIR

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches and caches market data"""

    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5 minute cache
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Rate limiting
        self.lock = threading.Lock()

        logger.info("Data Fetcher initialized")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        cache_key = f"price_{symbol}"

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Rate limiting
            self._rate_limit()

            # Fetch from yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")

            if not data.empty:
                price = data["Close"].iloc[-1]
                self.cache[cache_key] = price
                return price

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")

        return None

    def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """Get historical OHLCV data"""
        cache_key = f"hist_{symbol}_{period}_{interval}"

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Rate limiting
            self._rate_limit()

            # Fetch from yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)

            if not data.empty:
                self.cache[cache_key] = data
                return data

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")

        return pd.DataFrame()

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get prices for multiple symbols"""
        prices = {}

        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price:
                prices[symbol] = price

        return prices

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        with self.lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
            self.last_request_time = time.time()
