"""
OMNIBOT v2.6 Sentinel - Backtest Engine
Historical strategy testing
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from config.settings import BACKTEST, WATCHLIST
from src.core.data_fetcher import DataFetcher
from src.strategies.engine import StrategyEngine

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtesting engine for strategy evaluation"""

    def __init__(self):
        self.config = BACKTEST
        self.data_fetcher = DataFetcher()
        self.initial_capital = self.config.get("initial_capital", 100000.0)
        self.commission = self.config.get("commission", 0.001)
        self.slippage = self.config.get("slippage", 0.001)

        logger.info("Backtest Engine initialized")

    def run(self, start_date: str, end_date: str, symbols: Optional[List[str]] = None) -> Dict:
        """Run backtest for given period and symbols"""
        symbols = symbols or WATCHLIST[:5]  # Default to first 5 symbols

        logger.info(f"Starting backtest from {start_date} to {end_date}")
        logger.info(f"Symbols: {symbols}")

        results = {
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "trades": [],
            "equity_curve": [],
            "metrics": {}
        }

        capital = self.initial_capital
        positions = {}
        equity_curve = []
        trades = []

        for symbol in symbols:
            try:
                # Fetch historical data
                data = self.data_fetcher.get_historical_data(symbol, start=start_date, end=end_date)

                if data.empty:
                    logger.warning(f"No data for {symbol}")
                    continue

                # Simulate trading
                for i in range(20, len(data)):
                    current_data = data.iloc[:i+1]
                    current_price = current_data["Close"].iloc[-1]
                    current_date = current_data.index[-1]

                    # Simple momentum signal
                    returns = current_data["Close"].pct_change().iloc[-20:].mean()

                    # Trading logic
                    if returns > 0.02 and symbol not in positions:  # Buy signal
                        # Calculate position size
                        position_value = capital * 0.1  # 10% per position
                        quantity = int(position_value / current_price)

                        if quantity > 0:
                            cost = quantity * current_price * (1 + self.commission + self.slippage)

                            if cost <= capital:
                                capital -= cost
                                positions[symbol] = {
                                    "quantity": quantity,
                                    "entry_price": current_price,
                                    "entry_date": current_date
                                }

                                trades.append({
                                    "date": current_date,
                                    "symbol": symbol,
                                    "action": "buy",
                                    "price": current_price,
                                    "quantity": quantity,
                                    "value": cost
                                })

                    elif returns < -0.02 and symbol in positions:  # Sell signal
                        position = positions[symbol]
                        proceeds = position["quantity"] * current_price * (1 - self.commission - self.slippage)
                        pnl = proceeds - (position["quantity"] * position["entry_price"])

                        capital += proceeds

                        trades.append({
                            "date": current_date,
                            "symbol": symbol,
                            "action": "sell",
                            "price": current_price,
                            "quantity": position["quantity"],
                            "value": proceeds,
                            "pnl": pnl
                        })

                        del positions[symbol]

                    # Calculate equity
                    position_value = sum(
                        pos["quantity"] * current_data["Close"].iloc[-1]
                        for sym, pos in positions.items()
                        if sym == symbol
                    )
                    total_equity = capital + position_value

                    equity_curve.append({
                        "date": current_date,
                        "equity": total_equity
                    })

            except Exception as e:
                logger.error(f"Error backtesting {symbol}: {e}")

        # Calculate metrics
        results["trades"] = trades
        results["equity_curve"] = equity_curve
        results["metrics"] = self._calculate_metrics(equity_curve, trades)

        logger.info("Backtest completed")
        logger.info(f"Total return: {results['metrics'].get('total_return', 0):.2f}%")

        return results

    def _calculate_metrics(self, equity_curve: List[Dict], trades: List[Dict]) -> Dict:
        """Calculate performance metrics"""
        if not equity_curve:
            return {}

        equity_df = pd.DataFrame(equity_curve)
        equity_df.set_index("date", inplace=True)

        # Total return
        start_value = equity_df["equity"].iloc[0]
        end_value = equity_df["equity"].iloc[-1]
        total_return = (end_value - start_value) / start_value * 100

        # Daily returns
        equity_df["returns"] = equity_df["equity"].pct_change()

        # Sharpe ratio (simplified)
        avg_return = equity_df["returns"].mean()
        std_return = equity_df["returns"].std()
        sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0

        # Max drawdown
        equity_df["cummax"] = equity_df["equity"].cummax()
        equity_df["drawdown"] = (equity_df["equity"] - equity_df["cummax"]) / equity_df["cummax"]
        max_drawdown = equity_df["drawdown"].min() * 100

        # Win rate
        if trades:
            sell_trades = [t for t in trades if t["action"] == "sell"]
            winning_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
            win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0
        else:
            win_rate = 0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": len([t for t in trades if t["action"] == "sell"]),
            "final_equity": end_value
        }
