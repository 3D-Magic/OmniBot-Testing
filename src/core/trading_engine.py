"""
OMNIBOT v2.6 Sentinel - Trading Engine
Main trading logic and portfolio management
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from config.settings import TRADING, WATCHLIST, RISK
from src.core.data_fetcher import DataFetcher
from src.core.auto_updater import AutoUpdater
from src.strategies.engine import StrategyEngine

logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine that coordinates all components"""

    def __init__(self):
        self.config = TRADING
        self.running = False
        self.positions = {}
        self.cash = self.config.get("paper_capital", 100000.0)
        self.total_value = self.cash
        self.day_pnl = 0.0
        self.trades_today = 0

        # Initialize components
        self.data_fetcher = DataFetcher()
        self.strategy_engine = StrategyEngine()
        self.auto_updater = AutoUpdater()

        # Threads
        self.main_thread = None
        self.monitor_thread = None

        logger.info("Trading Engine initialized")

    def start(self):
        """Start the trading engine"""
        if self.running:
            logger.warning("Trading engine already running")
            return

        self.running = True
        logger.info(f"Starting OMNIBOT Trading Engine in {self.config.get('mode', 'paper')} mode")

        # Start auto-updater
        self.auto_updater.start()

        # Start strategy engine
        self.strategy_engine.start()

        # Start main trading loop
        self.main_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.main_thread.start()

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("Trading engine started successfully")

    def stop(self):
        """Stop the trading engine"""
        logger.info("Stopping trading engine...")
        self.running = False

        # Stop components
        self.auto_updater.stop()
        self.strategy_engine.stop()

        # Wait for threads
        if self.main_thread:
            self.main_thread.join(timeout=5)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Trading engine stopped")

    def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Check if market is open
                if not self._is_market_open():
                    logger.debug("Market closed - waiting")
                    time.sleep(60)
                    continue

                # Get signals from strategies
                signals = self.strategy_engine.generate_signals()

                # Process signals
                for signal in signals:
                    self._process_signal(signal)

                # Update portfolio value
                self._update_portfolio()

                # Sleep between cycles
                time.sleep(10)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(60)

    def _monitor_loop(self):
        """Monitoring and logging loop"""
        while self.running:
            try:
                # Log status every 5 minutes
                logger.info(f"Portfolio: ${self.total_value:,.2f} | Day P&L: ${self.day_pnl:,.2f} | Positions: {len(self.positions)}")
                time.sleep(300)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(60)

    def _is_market_open(self) -> bool:
        """Check if US market is open"""
        now = datetime.now()

        # Check weekday (Mon-Fri = 0-4)
        if now.weekday() >= 5:
            return False

        # Simplified market hours check (9:30 AM - 4:00 PM ET)
        # Note: This is simplified - doesn't account for timezone or holidays
        return True  # Allow trading for testing

    def _process_signal(self, signal: Dict):
        """Process a trading signal"""
        symbol = signal.get("symbol")
        action = signal.get("action")  # buy, sell, hold
        confidence = signal.get("confidence", 0)

        if action == "hold" or confidence < 0.6:
            return

        # Check risk limits
        if not self._check_risk_limits(symbol, action):
            return

        # Execute trade
        if action == "buy":
            self._execute_buy(symbol, signal)
        elif action == "sell":
            self._execute_sell(symbol, signal)

    def _check_risk_limits(self, symbol: str, action: str) -> bool:
        """Check if trade violates risk limits"""
        # Check max positions
        max_positions = self.config.get("max_positions", 10)
        if len(self.positions) >= max_positions and action == "buy":
            logger.warning(f"Max positions ({max_positions}) reached")
            return False

        # Check daily loss limit
        max_daily_loss = self.config.get("max_daily_loss", 0.05)
        if self.day_pnl < -self.total_value * max_daily_loss:
            logger.warning("Daily loss limit reached - stopping trading")
            return False

        return True

    def _execute_buy(self, symbol: str, signal: Dict):
        """Execute buy order"""
        try:
            # Get current price
            price = self.data_fetcher.get_current_price(symbol)
            if not price:
                logger.error(f"Could not get price for {symbol}")
                return

            # Calculate position size
            risk_per_trade = self.config.get("risk_per_trade", 0.02)
            position_value = self.total_value * risk_per_trade
            quantity = int(position_value / price)

            if quantity < 1:
                logger.warning(f"Insufficient funds to buy {symbol}")
                return

            # Check available cash
            cost = quantity * price
            if cost > self.cash:
                logger.warning(f"Insufficient cash to buy {symbol}")
                return

            # Execute paper trade
            self.cash -= cost
            self.positions[symbol] = {
                "quantity": quantity,
                "avg_price": price,
                "current_price": price,
                "value": cost
            }

            self.trades_today += 1
            logger.info(f"BUY {quantity} {symbol} @ ${price:.2f} = ${cost:.2f}")

        except Exception as e:
            logger.error(f"Buy execution error: {e}")

    def _execute_sell(self, symbol: str, signal: Dict):
        """Execute sell order"""
        try:
            if symbol not in self.positions:
                logger.warning(f"No position in {symbol} to sell")
                return

            position = self.positions[symbol]
            quantity = position["quantity"]

            # Get current price
            price = self.data_fetcher.get_current_price(symbol)
            if not price:
                price = position["current_price"]

            # Calculate proceeds
            proceeds = quantity * price
            pnl = proceeds - (quantity * position["avg_price"])

            # Update cash and remove position
            self.cash += proceeds
            self.day_pnl += pnl
            del self.positions[symbol]

            self.trades_today += 1
            logger.info(f"SELL {quantity} {symbol} @ ${price:.2f} = ${proceeds:.2f} (P&L: ${pnl:.2f})")

        except Exception as e:
            logger.error(f"Sell execution error: {e}")

    def _update_portfolio(self):
        """Update portfolio values"""
        try:
            total = self.cash

            for symbol, position in self.positions.items():
                # Get current price
                price = self.data_fetcher.get_current_price(symbol)
                if price:
                    position["current_price"] = price
                    position["value"] = position["quantity"] * price

                total += position["value"]

            self.total_value = total

        except Exception as e:
            logger.error(f"Portfolio update error: {e}")

    def get_status(self) -> Dict:
        """Get current trading status"""
        return {
            "running": self.running,
            "mode": self.config.get("mode", "paper"),
            "total_value": self.total_value,
            "cash": self.cash,
            "positions_count": len(self.positions),
            "day_pnl": self.day_pnl,
            "trades_today": self.trades_today
        }
