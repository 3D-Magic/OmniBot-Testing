"""
OMNIBOT v2.6 Sentinel - Data Fetcher
Fetches market data from free sources
"""

import logging
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import yfinance as yf
from alpaca_trade_api import REST
import time

from config.settings import EXCHANGES

logger = logging.getLogger(__name__)

class DataFetcher:
    """Fetches market data from multiple free sources"""

    def __init__(self):
        self.cache = {}
        self.cache_timeout = 60
        self.daily_cache_timeout = 3600
        self.session = None
        self.alpaca = None
        self._init_exchanges()

    def _init_exchanges(self):
        """Initialize exchange connections"""
        if EXCHANGES["alpaca"]["enabled"]:
            try:
                import os
                api_key = os.getenv("ALPACA_API_KEY", "")
                api_secret = os.getenv("ALPACA_SECRET_KEY", "")

                if api_key and api_secret:
                    self.alpaca = REST(
                        key_id=api_key,
                        secret_key=api_secret,
                        base_url=EXCHANGES["alpaca"]["paper_url"]
                    )
                    logger.info("Alpaca API initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Alpaca: {e}")

    async def initialize(self):
        """Initialize async session"""
        self.session = aiohttp.ClientSession()

    async def get_stock_data(self, 
                           symbol: str, 
                           period: str = "1d", 
                           interval: str = "1d") -> Optional[pd.DataFrame]:
        """Get stock OHLCV data"""
        cache_key = f"{symbol}_{period}_{interval}"

        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            timeout = self.cache_timeout if interval in ["1m", "2m", "5m", "15m", "30m"] else self.daily_cache_timeout

            if datetime.now() - cached_time < timedelta(seconds=timeout):
                return cached_data

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)

            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            data.columns = [col.lower().replace(" ", "_") for col in data.columns]
            self.cache[cache_key] = (datetime.now(), data)

            return data

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def get_multiple_stocks(self, 
                                 symbols: List[str], 
                                 period: str = "1d", 
                                 interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols concurrently"""
        tasks = [
            self.get_stock_data(symbol, period, interval)
            for symbol in symbols
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        data_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, pd.DataFrame):
                data_dict[symbol] = result
            elif isinstance(result, Exception):
                logger.error(f"Error fetching {symbol}: {result}")

        return data_dict

    async def get_real_time_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote (delayed 15-20 min for free tiers)"""
        try:
            if self.alpaca:
                quote = self.alpaca.get_latest_trade(symbol)
                return {
                    "symbol": symbol,
                    "price": quote.price,
                    "timestamp": quote.timestamp,
                    "source": "alpaca"
                }

            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "price": info.get("regularMarketPrice", 0),
                "change": info.get("regularMarketChange", 0),
                "change_percent": info.get("regularMarketChangePercent", 0),
                "timestamp": datetime.now(),
                "source": "yahoo"
            }

        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None

    async def get_market_status(self) -> Dict:
        """Get current market status"""
        try:
            now = datetime.now()
            et_time = now - timedelta(hours=5)

            is_weekday = et_time.weekday() < 5
            is_market_hours = 9 <= et_time.hour < 16 or (et_time.hour == 9 and et_time.minute >= 30)

            is_open = is_weekday and is_market_hours

            return {
                "is_open": is_open,
                "next_open": self._get_next_market_open(),
                "next_close": self._get_next_market_close(),
                "timestamp": now
            }

        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {"is_open": False, "error": str(e)}

    def _get_next_market_open(self) -> datetime:
        """Calculate next market open time"""
        now = datetime.now()
        et_now = now - timedelta(hours=5)

        if et_now.weekday() < 5 and (et_now.hour < 9 or (et_now.hour == 9 and et_now.minute < 30)):
            next_open = et_now.replace(hour=9, minute=30, second=0, microsecond=0)
        else:
            days_ahead = 1
            if et_now.weekday() >= 4:
                days_ahead = 7 - et_now.weekday()
            next_open = (et_now + timedelta(days=days_ahead)).replace(hour=9, minute=30, second=0, microsecond=0)

        return next_open + timedelta(hours=5)

    def _get_next_market_close(self) -> datetime:
        """Calculate next market close time"""
        now = datetime.now()
        et_now = now - timedelta(hours=5)

        if et_now.weekday() < 5 and et_now.hour < 16:
            next_close = et_now.replace(hour=16, minute=0, second=0, microsecond=0)
        else:
            days_ahead = 1
            if et_now.weekday() >= 4:
                days_ahead = 7 - et_now.weekday()
            next_close = (et_now + timedelta(days=days_ahead)).replace(hour=16, minute=0, second=0, microsecond=0)

        return next_close + timedelta(hours=5)

    async def get_watchlist_data(self, symbols: List[str]) -> pd.DataFrame:
        """Get summary data for watchlist"""
        data = []

        for symbol in symbols:
            try:
                quote = await self.get_real_time_quote(symbol)
                if quote:
                    data.append({
                        "symbol": symbol,
                        "price": quote.get("price", 0),
                        "change": quote.get("change", 0),
                        "change_percent": quote.get("change_percent", 0)
                    })
            except Exception as e:
                logger.debug(f"Error getting watchlist data for {symbol}: {e}")

        return pd.DataFrame(data)

    def clear_cache(self):
        """Clear data cache"""
        self.cache.clear()
        logger.info("Data cache cleared")

    async def close(self):
        """Close connections"""
        if self.session:
            await self.session.close()
