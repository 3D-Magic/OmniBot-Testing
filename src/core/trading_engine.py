"""
OMNIBOT Trading Engine
Handles order execution, position management, and risk controls
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from config.settings import TRADING, STRATEGIES

logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    side: str  # 'long' or 'short'
    entry_time: datetime

    @property
    def pnl(self) -> float:
        if self.side == 'long':
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def pnl_percent(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == 'long':
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100


class TradingEngine:
    """Main trading engine for OMNIBOT"""

    def __init__(self):
        self.mode = TRADING.get('mode', 'paper')
        self.max_positions = TRADING.get('max_positions', 10)
        self.risk_per_trade = TRADING.get('risk_per_trade', 0.02)
        self.max_daily_loss = TRADING.get('max_daily_loss', 0.05)
        self.paper_balance = TRADING.get('paper_balance', 10000.0)
        self.watchlist = TRADING.get('watchlist', [])

        self.positions: Dict[str, Position] = {}
        self.orders_history: List[Dict] = []
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.is_running = False

        logger.info(f"TradingEngine initialized (mode: {self.mode})")

    def start(self):
        """Start the trading engine"""
        self.is_running = True
        logger.info("Trading engine started")

    def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        logger.info("Trading engine stopped")

    def enter_position(self, symbol: str, side: str, quantity: float, 
                       price: float, strategy: str = "manual") -> bool:
        """Enter a new position"""
        if not self.is_running:
            logger.warning("Cannot enter position - engine not running")
            return False

        if len(self.positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached")
            return False

        if symbol in self.positions:
            logger.warning(f"Position already exists for {symbol}")
            return False

        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            current_price=price,
            side=side,
            entry_time=datetime.now()
        )

        self.positions[symbol] = position

        order = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat(),
            'type': 'entry'
        }
        self.orders_history.append(order)

        logger.info(f"Entered {side} position: {symbol} @ ${price:.2f} x {quantity}")
        return True

    def exit_position(self, symbol: str, price: float, 
                      reason: str = "manual") -> Optional[float]:
        """Exit an existing position"""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return None

        position = self.positions[symbol]
        position.current_price = price
        pnl = position.pnl

        order = {
            'symbol': symbol,
            'side': 'exit',
            'quantity': position.quantity,
            'price': price,
            'pnl': pnl,
            'pnl_percent': position.pnl_percent,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'type': 'exit'
        }
        self.orders_history.append(order)

        # Update stats
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        self.daily_pnl += pnl

        if self.mode == 'paper':
            self.paper_balance += pnl

        del self.positions[symbol]

        logger.info(f"Exited {symbol} @ ${price:.2f} | P&L: ${pnl:.2f} ({position.pnl_percent:.2f}%)")
        return pnl

    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for all positions"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price

    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        if self.mode == 'paper':
            positions_value = sum(p.current_price * p.quantity for p in self.positions.values())
            return self.paper_balance + positions_value
        return 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get trading statistics"""
        return {
            'mode': self.mode,
            'is_running': self.is_running,
            'positions_count': len(self.positions),
            'total_trades': self.total_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'daily_pnl': self.daily_pnl,
            'portfolio_value': self.get_portfolio_value(),
            'paper_balance': self.paper_balance if self.mode == 'paper' else None
        }

    def check_risk_limits(self) -> bool:
        """Check if risk limits are breached"""
        portfolio_value = self.get_portfolio_value()
        if portfolio_value == 0:
            return True

        daily_loss_percent = abs(self.daily_pnl) / portfolio_value
        if daily_loss_percent >= self.max_daily_loss:
            logger.warning(f"Daily loss limit reached: {daily_loss_percent:.2%}")
            return False

        return True


def create_engine() -> TradingEngine:
    """Factory function to create trading engine"""
    return TradingEngine()
