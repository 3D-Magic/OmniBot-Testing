"""
OMNIBOT v2.6 Sentinel - Strategy Engine
Multi-strategy coordination and signal generation
"""

import logging
import threading
import time
from typing import Dict, List
from collections import defaultdict

from config.settings import STRATEGIES, WATCHLIST
from src.core.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Manages multiple trading strategies"""

    def __init__(self):
        self.config = STRATEGIES
        self.data_fetcher = DataFetcher()
        self.running = False
        self.signals = []
        self.thread = None

        # Initialize strategies
        self.strategies = {}
        self._init_strategies()

        logger.info("Strategy Engine initialized")

    def _init_strategies(self):
        """Initialize enabled strategies"""
        if self.config.get("momentum", {}).get("enabled", False):
            self.strategies["momentum"] = MomentumStrategy(self.config["momentum"])

        if self.config.get("mean_reversion", {}).get("enabled", False):
            self.strategies["mean_reversion"] = MeanReversionStrategy(self.config["mean_reversion"])

        if self.config.get("breakout", {}).get("enabled", False):
            self.strategies["breakout"] = BreakoutStrategy(self.config["breakout"])

        if self.config.get("ml_ensemble", {}).get("enabled", False):
            self.strategies["ml_ensemble"] = MLEnsembleStrategy(self.config["ml_ensemble"])

        logger.info(f"Initialized {len(self.strategies)} strategies")

    def start(self):
        """Start strategy engine"""
        self.running = True
        self.thread = threading.Thread(target=self._strategy_loop, daemon=True)
        self.thread.start()
        logger.info("Strategy engine started")

    def stop(self):
        """Stop strategy engine"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Strategy engine stopped")

    def _strategy_loop(self):
        """Main strategy loop"""
        while self.running:
            try:
                self.generate_signals()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Strategy loop error: {e}")
                time.sleep(60)

    def generate_signals(self) -> List[Dict]:
        """Generate trading signals from all strategies"""
        all_signals = []

        for symbol in WATCHLIST:
            try:
                # Get data
                data = self.data_fetcher.get_historical_data(symbol, period="5d", interval="5m")

                if data.empty:
                    continue

                # Get signals from each strategy
                for name, strategy in self.strategies.items():
                    signal = strategy.generate_signal(symbol, data)
                    if signal and signal.get("action") != "hold":
                        all_signals.append(signal)

            except Exception as e:
                logger.error(f"Error generating signals for {symbol}: {e}")

        self.signals = all_signals
        return all_signals

    def get_strategy_status(self) -> Dict:
        """Get status of all strategies"""
        return {
            name: {
                "enabled": True,
                "weight": self.config.get(name, {}).get("weight", 0.25)
            }
            for name in self.strategies.keys()
        }


class MomentumStrategy:
    """Momentum-based strategy"""

    def __init__(self, config):
        self.config = config
        self.lookback = config.get("params", {}).get("lookback", 20)
        self.threshold = config.get("params", {}).get("threshold", 0.05)

    def generate_signal(self, symbol: str, data) -> Dict:
        """Generate momentum signal"""
        if len(data) < self.lookback:
            return {"symbol": symbol, "action": "hold", "confidence": 0}

        # Calculate momentum
        current_price = data["Close"].iloc[-1]
        past_price = data["Close"].iloc[-self.lookback]
        momentum = (current_price - past_price) / past_price

        # Generate signal
        if momentum > self.threshold:
            return {
                "symbol": symbol,
                "action": "buy",
                "confidence": min(abs(momentum) * 10, 1.0),
                "strategy": "momentum",
                "metadata": {"momentum": momentum}
            }
        elif momentum < -self.threshold:
            return {
                "symbol": symbol,
                "action": "sell",
                "confidence": min(abs(momentum) * 10, 1.0),
                "strategy": "momentum",
                "metadata": {"momentum": momentum}
            }

        return {"symbol": symbol, "action": "hold", "confidence": 0}


class MeanReversionStrategy:
    """Mean reversion strategy"""

    def __init__(self, config):
        self.config = config
        self.lookback = config.get("params", {}).get("lookback", 20)
        self.z_threshold = config.get("params", {}).get("z_score_threshold", 2.0)

    def generate_signal(self, symbol: str, data) -> Dict:
        """Generate mean reversion signal"""
        if len(data) < self.lookback:
            return {"symbol": symbol, "action": "hold", "confidence": 0}

        # Calculate z-score
        prices = data["Close"]
        mean = prices.rolling(window=self.lookback).mean().iloc[-1]
        std = prices.rolling(window=self.lookback).std().iloc[-1]
        current_price = prices.iloc[-1]

        if std == 0:
            return {"symbol": symbol, "action": "hold", "confidence": 0}

        z_score = (current_price - mean) / std

        # Generate signal (buy when oversold, sell when overbought)
        if z_score < -self.z_threshold:
            return {
                "symbol": symbol,
                "action": "buy",
                "confidence": min(abs(z_score) / 4, 1.0),
                "strategy": "mean_reversion",
                "metadata": {"z_score": z_score}
            }
        elif z_score > self.z_threshold:
            return {
                "symbol": symbol,
                "action": "sell",
                "confidence": min(abs(z_score) / 4, 1.0),
                "strategy": "mean_reversion",
                "metadata": {"z_score": z_score}
            }

        return {"symbol": symbol, "action": "hold", "confidence": 0}


class BreakoutStrategy:
    """Breakout strategy"""

    def __init__(self, config):
        self.config = config
        self.atr_period = config.get("params", {}).get("atr_period", 14)
        self.breakout_factor = config.get("params", {}).get("breakout_factor", 1.5)

    def generate_signal(self, symbol: str, data) -> Dict:
        """Generate breakout signal"""
        if len(data) < self.atr_period + 5:
            return {"symbol": symbol, "action": "hold", "confidence": 0}

        # Calculate ATR
        high_low = data["High"] - data["Low"]
        high_close = abs(data["High"] - data["Close"].shift())
        low_close = abs(data["Low"] - data["Close"].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=self.atr_period).mean().iloc[-1]

        # Get price levels
        current_price = data["Close"].iloc[-1]
        prev_high = data["High"].iloc[-5:-1].max()
        prev_low = data["Low"].iloc[-5:-1].min()

        # Breakout detection
        if current_price > prev_high + atr * self.breakout_factor:
            return {
                "symbol": symbol,
                "action": "buy",
                "confidence": 0.7,
                "strategy": "breakout",
                "metadata": {"breakout_type": "up"}
            }
        elif current_price < prev_low - atr * self.breakout_factor:
            return {
                "symbol": symbol,
                "action": "sell",
                "confidence": 0.7,
                "strategy": "breakout",
                "metadata": {"breakout_type": "down"}
            }

        return {"symbol": symbol, "action": "hold", "confidence": 0}


class MLEnsembleStrategy:
    """Machine Learning ensemble strategy"""

    def __init__(self, config):
        self.config = config
        self.sequence_length = config.get("params", {}).get("sequence_length", 60)
        self.confidence_threshold = config.get("params", {}).get("confidence_threshold", 0.6)

    def generate_signal(self, symbol: str, data) -> Dict:
        """Generate ML-based signal (simplified)"""
        if len(data) < self.sequence_length:
            return {"symbol": symbol, "action": "hold", "confidence": 0}

        # Simplified ML signal based on trend and volume
        prices = data["Close"]
        volumes = data["Volume"]

        # Calculate features
        returns = prices.pct_change().iloc[-10:].mean()
        volume_trend = volumes.iloc[-5:].mean() / volumes.iloc[-20:].mean() - 1

        # Simple ensemble logic
        score = returns * 10 + volume_trend * 5
        confidence = min(abs(score), 1.0)

        if confidence > self.confidence_threshold:
            action = "buy" if score > 0 else "sell"
            return {
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "strategy": "ml_ensemble",
                "metadata": {"score": score}
            }

        return {"symbol": symbol, "action": "hold", "confidence": 0}
