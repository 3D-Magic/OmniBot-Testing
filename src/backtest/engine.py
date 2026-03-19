"""
OMNIBOT v2.6 Sentinel - Backtesting Engine
Test strategies on historical data
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import json

from config.settings import BACKTEST, CURRENT_HARDWARE
from src.strategies.engine import StrategyEngine, Signal

logger = logging.getLogger(__name__)

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Backtest order"""
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0

@dataclass
class Position:
    """Backtest position"""
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.current_price - self.avg_entry_price)

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_entry_price == 0:
            return 0
        return (self.current_price - self.avg_entry_price) / self.avg_entry_price

@dataclass
class BacktestResult:
    """Complete backtest results"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    profit_factor: float
    equity_curve: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "avg_trade_return": self.avg_trade_return,
            "avg_winning_trade": self.avg_winning_trade,
            "avg_losing_trade": self.avg_losing_trade,
            "profit_factor": self.profit_factor,
            "equity_curve": self.equity_curve,
            "monthly_returns": self.monthly_returns
        }

    def save(self, filepath: str):
        """Save results to JSON"""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

class BacktestEngine:
    """Engine for backtesting trading strategies"""

    def __init__(self, 
                 initial_capital: float = None,
                 commission: float = None,
                 slippage: float = None):
        self.initial_capital = initial_capital or BACKTEST["initial_capital"]
        self.commission = commission or BACKTEST["commission"]
        self.slippage = slippage or BACKTEST["slippage"]
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.strategy_engine = StrategyEngine()

    def reset(self):
        """Reset engine state"""
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []
        self.equity_curve = []

    def run_backtest(self,
                     data: Dict[str, pd.DataFrame],
                     start_date: datetime = None,
                     end_date: datetime = None) -> BacktestResult:
        """
        Run backtest on historical data

        Args:
            data: Dict of symbol -> DataFrame with OHLCV data
            start_date: Start date for backtest
            end_date: End date for backtest
        """
        self.reset()

        # Filter date range
        if start_date or end_date:
            filtered_data = {}
            for symbol, df in data.items():
                mask = True
                if start_date:
                    mask = mask & (df.index >= start_date)
                if end_date:
                    mask = mask & (df.index <= end_date)
                filtered_data[symbol] = df[mask]
            data = filtered_data

        # Get all dates
        all_dates = set()
        for df in data.values():
            all_dates.update(df.index)
        sorted_dates = sorted(all_dates)

        if not sorted_dates:
            logger.error("No data available for backtest")
            return None

        logger.info(f"Running backtest from {sorted_dates[0]} to {sorted_dates[-1]}")

        # Iterate through each day
        for current_date in sorted_dates:
            # Update positions with current prices
            self._update_positions(data, current_date)

            # Generate signals for each symbol
            for symbol, df in data.items():
                if current_date not in df.index:
                    continue

                # Get data up to current date
                current_data = df[df.index <= current_date]

                if len(current_data) < 20:  # Need minimum data
                    continue

                # Get signals from strategies
                signals = asyncio.run(
                    self.strategy_engine.analyze_symbol(symbol, current_data)
                )

                # Combine signals
                consensus = self.strategy_engine.combine_signals(signals)

                if consensus and consensus.direction != "hold":
                    self._execute_signal(consensus, current_date, current_data)

            # Record equity
            self._record_equity(current_date)

        # Calculate results
        return self._calculate_results(sorted_dates[0], sorted_dates[-1])

    def _update_positions(self, data: Dict[str, pd.DataFrame], current_date: datetime):
        """Update position prices"""
        for symbol, position in self.positions.items():
            if symbol in data and current_date in data[symbol].index:
                position.current_price = data[symbol].loc[current_date, "close"]

    def _execute_signal(self, signal: Signal, timestamp: datetime, data: pd.DataFrame):
        """Execute trading signal"""
        symbol = signal.symbol
        current_price = data["close"].iloc[-1]

        # Apply slippage
        if signal.direction == "buy":
            execution_price = current_price * (1 + self.slippage)
        else:
            execution_price = current_price * (1 - self.slippage)

        # Calculate position size (fixed 10% of portfolio per trade)
        portfolio_value = self._get_portfolio_value()
        trade_value = portfolio_value * 0.10
        quantity = trade_value / execution_price

        if signal.direction == "buy":
            # Check if we have enough cash
            cost = quantity * execution_price * (1 + self.commission)
            if cost > self.cash:
                quantity = self.cash / (execution_price * (1 + self.commission))
                cost = quantity * execution_price * (1 + self.commission)

            if quantity <= 0:
                return

            # Execute buy
            self.cash -= cost

            if symbol in self.positions:
                # Update existing position
                pos = self.positions[symbol]
                total_cost = pos.quantity * pos.avg_entry_price + quantity * execution_price
                pos.quantity += quantity
                pos.avg_entry_price = total_cost / pos.quantity
            else:
                # New position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=execution_price,
                    current_price=execution_price
                )

            side = OrderSide.BUY

        else:  # sell
            if symbol not in self.positions or self.positions[symbol].quantity <= 0:
                return

            pos = self.positions[symbol]
            sell_quantity = min(quantity, pos.quantity)

            # Calculate P&L
            pnl = sell_quantity * (execution_price - pos.avg_entry_price)
            pnl_pct = (execution_price - pos.avg_entry_price) / pos.avg_entry_price

            # Execute sell
            proceeds = sell_quantity * execution_price * (1 - self.commission)
            self.cash += proceeds

            # Record trade
            self.trades.append({
                "symbol": symbol,
                "side": "sell",
                "quantity": sell_quantity,
                "entry_price": pos.avg_entry_price,
                "exit_price": execution_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "timestamp": timestamp.isoformat()
            })

            # Update position
            pos.quantity -= sell_quantity
            if pos.quantity <= 0:
                del self.positions[symbol]

            side = OrderSide.SELL

        # Record order
        self.orders.append(Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=execution_price,
            timestamp=timestamp,
            commission=quantity * execution_price * self.commission
        ))

    def _get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value

    def _record_equity(self, timestamp: datetime):
        """Record equity point"""
        self.equity_curve.append({
            "timestamp": timestamp.isoformat(),
            "equity": self._get_portfolio_value(),
            "cash": self.cash,
            "positions": len(self.positions)
        })

    def _calculate_results(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Calculate final backtest metrics"""
        final_value = self._get_portfolio_value()
        total_return = final_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        # Calculate daily returns for Sharpe ratio
        equity_df = pd.DataFrame(self.equity_curve)
        if len(equity_df) > 1:
            equity_df["timestamp"] = pd.to_datetime(equity_df["timestamp"])
            equity_df.set_index("timestamp", inplace=True)
            equity_df["returns"] = equity_df["equity"].pct_change()

            # Sharpe ratio (annualized, assuming 252 trading days)
            avg_return = equity_df["returns"].mean()
            std_return = equity_df["returns"].std()
            sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0

            # Max drawdown
            equity_df["peak"] = equity_df["equity"].expanding().max()
            equity_df["drawdown"] = (equity_df["equity"] - equity_df["peak"]) / equity_df["peak"]
            max_drawdown = equity_df["drawdown"].min()
            max_drawdown_pct = max_drawdown * 100

            # Monthly returns
            monthly = equity_df["returns"].resample("M").apply(lambda x: (1 + x).prod() - 1)
            monthly_returns = {k.strftime("%Y-%m"): v for k, v in monthly.items()}
        else:
            sharpe = 0
            max_drawdown = 0
            max_drawdown_pct = 0
            monthly_returns = {}

        # Trade statistics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t["pnl"] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        avg_trade_return = np.mean([t["pnl_pct"] for t in self.trades]) if self.trades else 0
        avg_win = np.mean([t["pnl_pct"] for t in self.trades if t["pnl"] > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t["pnl_pct"] for t in self.trades if t["pnl"] <= 0]) if losing_trades > 0 else 0

        gross_profit = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in self.trades if t["pnl"] <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        return BacktestResult(
            strategy_name="Multi-Strategy",
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_win,
            avg_losing_trade=avg_loss,
            profit_factor=profit_factor,
            equity_curve=self.equity_curve,
            trades=self.trades,
            monthly_returns=monthly_returns
        )

    def optimize_parameters(self,
                          data: Dict[str, pd.DataFrame],
                          param_grid: Dict[str, List[Any]],
                          metric: str = "sharpe_ratio") -> Dict:
        """
        Optimize strategy parameters using grid search

        Args:
            data: Historical data
            param_grid: Dict of parameter names to list of values
            metric: Metric to optimize (sharpe_ratio, total_return, etc.)
        """
        logger.info(f"Starting parameter optimization with {len(param_grid)} parameters")

        best_result = None
        best_score = -float("inf")
        best_params = {}

        # Simple grid search (can be parallelized)
        from itertools import product

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        total_combinations = 1
        for v in values:
            total_combinations *= len(v)

        logger.info(f"Testing {total_combinations} parameter combinations")

        for combination in product(*values):
            params = dict(zip(keys, combination))

            # Update strategy parameters
            for strategy in self.strategy_engine.strategies.values():
                for key, value in params.items():
                    if key in strategy.parameters:
                        strategy.parameters[key] = value

            # Run backtest
            result = self.run_backtest(data)

            if result:
                score = getattr(result, metric, 0)

                if score > best_score:
                    best_score = score
                    best_result = result
                    best_params = params.copy()

        logger.info(f"Optimization complete. Best {metric}: {best_score}")
        logger.info(f"Best parameters: {best_params}")

        return {
            "best_params": best_params,
            "best_score": best_score,
            "result": best_result
        }
