"""
OMNIBOT v2.6 Sentinel - Trading Engine
Main trading logic and execution
"""

import logging
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import pandas as pd

from config.settings import TRADING, VERSION, VERSION_NAME
from src.core.data_fetcher import DataFetcher
from src.strategies.engine import StrategyEngine, Signal
from src.sentiment.analyzer import SentimentAnalyzer
from src.core.auto_updater import AutoUpdater

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"

@dataclass
class Trade:
    """Trade execution record"""
    id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    strategy: str
    pnl: float = 0.0
    status: str = "pending"  # pending, filled, cancelled, failed

@dataclass
class Position:
    """Current position"""
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    strategy: str

class Portfolio:
    """Portfolio management"""

    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.initial_value = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0

    @property
    def total_value(self) -> float:
        """Total portfolio value"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value

    @property
    def positions_value(self) -> float:
        """Value of all positions"""
        return sum(pos.market_value for pos in self.positions.values())

    def update_prices(self, prices: Dict[str, float]):
        """Update position prices"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.current_price = price
                pos.market_value = pos.quantity * price
                pos.unrealized_pnl = pos.quantity * (price - pos.avg_entry_price)
                pos.unrealized_pnl_pct = (price - pos.avg_entry_price) / pos.avg_entry_price if pos.avg_entry_price > 0 else 0

    def add_trade(self, trade: Trade):
        """Add trade to history and update positions"""
        self.trades.append(trade)

        if trade.status == "filled":
            if trade.side == "buy":
                # Update or create position
                if trade.symbol in self.positions:
                    pos = self.positions[trade.symbol]
                    total_cost = pos.quantity * pos.avg_entry_price + trade.quantity * trade.price
                    pos.quantity += trade.quantity
                    pos.avg_entry_price = total_cost / pos.quantity
                else:
                    self.positions[trade.symbol] = Position(
                        symbol=trade.symbol,
                        quantity=trade.quantity,
                        avg_entry_price=trade.price,
                        current_price=trade.price,
                        market_value=trade.quantity * trade.price,
                        unrealized_pnl=0.0,
                        unrealized_pnl_pct=0.0,
                        strategy=trade.strategy
                    )

                self.cash -= trade.quantity * trade.price

            else:  # sell
                if trade.symbol in self.positions:
                    pos = self.positions[trade.symbol]

                    # Calculate realized P&L
                    realized_pnl = trade.quantity * (trade.price - pos.avg_entry_price)
                    self.total_pnl += realized_pnl
                    self.daily_pnl += realized_pnl

                    # Update position
                    pos.quantity -= trade.quantity
                    self.cash += trade.quantity * trade.price

                    if pos.quantity <= 0:
                        del self.positions[trade.symbol]

    def get_metrics(self) -> Dict:
        """Get portfolio metrics"""
        return {
            "total_value": self.total_value,
            "cash": self.cash,
            "positions_value": self.positions_value,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.initial_value) * 100 if self.initial_value > 0 else 0,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": ((self.total_value - self.initial_value) / self.initial_value) * 100 if self.initial_value > 0 else 0,
            "num_positions": len(self.positions),
            "buying_power": self.cash
        }

class TradingEngine:
    """Main trading engine"""

    def __init__(self):
        self.version = VERSION
        self.version_name = VERSION_NAME
        self.mode = TradingMode(TRADING["mode"])
        self.running = False

        # Initialize components
        self.data_fetcher = DataFetcher()
        self.strategy_engine = StrategyEngine()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.auto_updater = AutoUpdater()

        # Portfolio
        self.portfolio = Portfolio(initial_cash=TRADING.get("initial_capital", 100000.0))

        # Watchlist
        self.watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]

        # Risk management
        self.max_positions = TRADING.get("max_positions", 10)
        self.risk_per_trade = TRADING.get("risk_per_trade", 0.02)
        self.max_daily_loss = TRADING.get("max_daily_loss", 0.05)

        logger.info(f"OMNIBOT v{self.version} {self.version_name} initialized")
        logger.info(f"Trading mode: {self.mode.value}")

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing trading engine...")

        await self.data_fetcher.initialize()
        await self.sentiment_analyzer.initialize()

        # Start auto-updater
        self.auto_updater.start()

        logger.info("Trading engine initialized successfully")

    async def start(self):
        """Start trading loop"""
        self.running = True
        logger.info("Trading engine started")

        while self.running:
            try:
                # Check market status
                market_status = await self.data_fetcher.get_market_status()

                if not market_status["is_open"]:
                    logger.debug("Markets closed - waiting...")
                    await asyncio.sleep(60)
                    continue

                # Check daily loss limit
                metrics = self.portfolio.get_metrics()
                daily_loss_pct = abs(metrics["daily_pnl_pct"])

                if daily_loss_pct >= self.max_daily_loss * 100:
                    logger.warning(f"Daily loss limit reached: {daily_loss_pct:.2f}% - stopping trading")
                    self.running = False
                    break

                # Fetch data for watchlist
                data = await self.data_fetcher.get_multiple_stocks(
                    self.watchlist, 
                    period="5d", 
                    interval="1d"
                )

                # Analyze each symbol
                for symbol, df in data.items():
                    if df is None or len(df) < 20:
                        continue

                    # Get strategy signals
                    signals = await self.strategy_engine.analyze_symbol(symbol, df)
                    consensus = self.strategy_engine.combine_signals(signals)

                    # Get sentiment
                    sentiment = await self.sentiment_analyzer.analyze_symbol(symbol)

                    # Combine with sentiment if available
                    if sentiment and abs(sentiment.score) > 0.2:
                        sentiment_adjustment = sentiment.score * 0.15  # 15% weight
                        consensus.strength = min(1.0, consensus.strength + sentiment_adjustment)

                    # Execute signal
                    if consensus.direction != "hold" and consensus.strength > 0.5:
                        await self._execute_signal(consensus)

                # Update portfolio prices
                await self._update_portfolio_prices()

                # Sleep until next iteration
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop trading engine"""
        self.running = False
        self.auto_updater.stop()
        await self.data_fetcher.close()
        await self.sentiment_analyzer.close()
        logger.info("Trading engine stopped")

    async def _execute_signal(self, signal: Signal):
        """Execute trading signal"""
        try:
            # Check position limits
            if signal.direction == "buy" and len(self.portfolio.positions) >= self.max_positions:
                if signal.symbol not in self.portfolio.positions:
                    logger.debug(f"Max positions reached - skipping {signal.symbol}")
                    return

            # Get current price
            quote = await self.data_fetcher.get_real_time_quote(signal.symbol)
            if not quote:
                return

            current_price = quote["price"]

            # Calculate position size
            portfolio_value = self.portfolio.total_value
            risk_amount = portfolio_value * self.risk_per_trade

            if signal.direction == "buy":
                # Simple position sizing - 10% of portfolio per trade
                position_value = portfolio_value * 0.10
                quantity = int(position_value / current_price)

                if quantity <= 0:
                    return

                # Check if we have enough cash
                cost = quantity * current_price
                if cost > self.portfolio.cash:
                    logger.warning(f"Insufficient cash for {signal.symbol} trade")
                    return

                # Execute buy
                trade = Trade(
                    id=f"{signal.symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    symbol=signal.symbol,
                    side="buy",
                    quantity=quantity,
                    price=current_price,
                    timestamp=datetime.now(),
                    strategy=signal.strategy,
                    status="filled" if self.mode == TradingMode.PAPER else "pending"
                )

                self.portfolio.add_trade(trade)
                logger.info(f"BUY {quantity} shares of {signal.symbol} @ ${current_price:.2f}")

            else:  # sell
                if signal.symbol not in self.portfolio.positions:
                    return

                position = self.portfolio.positions[signal.symbol]
                quantity = position.quantity  # Sell entire position

                trade = Trade(
                    id=f"{signal.symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    symbol=signal.symbol,
                    side="sell",
                    quantity=quantity,
                    price=current_price,
                    timestamp=datetime.now(),
                    strategy=signal.strategy,
                    status="filled" if self.mode == TradingMode.PAPER else "pending"
                )

                self.portfolio.add_trade(trade)
                logger.info(f"SELL {quantity} shares of {signal.symbol} @ ${current_price:.2f}")

        except Exception as e:
            logger.error(f"Error executing signal: {e}")

    async def _update_portfolio_prices(self):
        """Update current prices for all positions"""
        if not self.portfolio.positions:
            return

        symbols = list(self.portfolio.positions.keys())
        prices = {}

        for symbol in symbols:
            quote = await self.data_fetcher.get_real_time_quote(symbol)
            if quote:
                prices[symbol] = quote["price"]

        self.portfolio.update_prices(prices)

    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            "version": self.version,
            "version_name": self.version_name,
            "mode": self.mode.value,
            "running": self.running,
            "portfolio": self.portfolio.get_metrics(),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_entry_price,
                    "current_price": pos.current_price,
                    "pnl": pos.unrealized_pnl,
                    "pnl_pct": pos.unrealized_pnl_pct * 100
                }
                for pos in self.portfolio.positions.values()
            ],
            "recent_trades": [
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "quantity": t.quantity,
                    "price": t.price,
                    "timestamp": t.timestamp.isoformat(),
                    "strategy": t.strategy
                }
                for t in self.portfolio.trades[-10:]  # Last 10 trades
            ]
        }

    def add_to_watchlist(self, symbol: str):
        """Add symbol to watchlist"""
        symbol = symbol.upper()
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            logger.info(f"Added {symbol} to watchlist")

    def remove_from_watchlist(self, symbol: str):
        """Remove symbol from watchlist"""
        symbol = symbol.upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")
