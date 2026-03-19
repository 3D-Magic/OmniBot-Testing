"""
OMNIBOT v2.6 Sentinel - Multi-Strategy Engine
Manages multiple trading strategies simultaneously
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from config.settings import STRATEGIES, CURRENT_HARDWARE

logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """Trading signal from a strategy"""
    strategy: str
    symbol: str
    direction: str  # buy, sell, hold
    strength: float  # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any]

class StrategyBase:
    """Base class for all strategies"""

    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", False)
        self.weight = config.get("weight", 0.25)
        self.parameters = config.get("parameters", {})
        self.performance_history = []

    async def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        """Analyze market data and return signal"""
        raise NotImplementedError

    def get_performance(self) -> Dict:
        """Return strategy performance metrics"""
        if not self.performance_history:
            return {"sharpe": 0, "win_rate": 0, "total_return": 0}

        returns = [p["return"] for p in self.performance_history]
        return {
            "sharpe": np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252),
            "win_rate": sum(1 for r in returns if r > 0) / len(returns),
            "total_return": sum(returns),
            "trades": len(self.performance_history)
        }

    def update_performance(self, trade_result: Dict):
        """Update strategy with trade result"""
        self.performance_history.append(trade_result)
        # Keep last 100 trades
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

class MomentumStrategy(StrategyBase):
    """Momentum-based strategy using price trends"""

    async def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        if not self.enabled or len(data) < self.parameters["lookback"]:
            return None

        lookback = self.parameters["lookback"]
        threshold = self.parameters["threshold"]

        # Calculate momentum
        current_price = data["close"].iloc[-1]
        past_price = data["close"].iloc[-lookback]
        momentum = (current_price - past_price) / past_price

        # Generate signal
        if momentum > threshold:
            direction = "buy"
            strength = min(abs(momentum) / threshold, 1.0)
        elif momentum < -threshold:
            direction = "sell"
            strength = min(abs(momentum) / threshold, 1.0)
        else:
            direction = "hold"
            strength = 0.0

        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            strength=strength * self.weight,
            timestamp=datetime.now(),
            metadata={"momentum": momentum, "lookback": lookback}
        )

class MeanReversionStrategy(StrategyBase):
    """Mean reversion strategy using z-scores"""

    async def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        if not self.enabled or len(data) < self.parameters["lookback"]:
            return None

        lookback = self.parameters["lookback"]
        threshold = self.parameters["z_score_threshold"]

        # Calculate z-score
        mean = data["close"].tail(lookback).mean()
        std = data["close"].tail(lookback).std()

        if std == 0:
            return None

        current_price = data["close"].iloc[-1]
        z_score = (current_price - mean) / std

        # Mean reversion: buy when z-score is very negative, sell when very positive
        if z_score < -threshold:
            direction = "buy"
            strength = min(abs(z_score) / threshold, 1.0)
        elif z_score > threshold:
            direction = "sell"
            strength = min(abs(z_score) / threshold, 1.0)
        else:
            direction = "hold"
            strength = 0.0

        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            strength=strength * self.weight,
            timestamp=datetime.now(),
            metadata={"z_score": z_score, "mean": mean, "std": std}
        )

class BreakoutStrategy(StrategyBase):
    """Breakout strategy using ATR"""

    async def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        if not self.enabled or len(data) < self.parameters["atr_period"]:
            return None

        atr_period = self.parameters["atr_period"]
        breakout_factor = self.parameters["breakout_factor"]

        # Calculate ATR
        high_low = data["high"] - data["low"]
        high_close = abs(data["high"] - data["close"].shift())
        low_close = abs(data["low"] - data["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_period).mean().iloc[-1]

        # Get recent range
        recent_high = data["high"].tail(atr_period).max()
        recent_low = data["low"].tail(atr_period).min()

        current_price = data["close"].iloc[-1]

        # Breakout detection
        if current_price > recent_high - (atr * breakout_factor):
            direction = "buy"
            strength = min((current_price - recent_low) / (recent_high - recent_low), 1.0)
        elif current_price < recent_low + (atr * breakout_factor):
            direction = "sell"
            strength = min((recent_high - current_price) / (recent_high - recent_low), 1.0)
        else:
            direction = "hold"
            strength = 0.0

        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            strength=strength * self.weight,
            timestamp=datetime.now(),
            metadata={"atr": atr, "recent_high": recent_high, "recent_low": recent_low}
        )

class MLEnsembleStrategy(StrategyBase):
    """Machine Learning ensemble strategy"""

    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.model = None
        self.scaler = None
        self._load_model()

    def _load_model(self):
        """Load pre-trained ML model"""
        try:
            import joblib
            model_path = f"src/ml/models/{self.parameters.get("model_type", "lstm")}_model.pkl"
            self.model = joblib.load(model_path)
            logger.info(f"Loaded ML model: {model_path}")
        except Exception as e:
            logger.warning(f"Could not load ML model: {e}")
            self.model = None

    async def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        if not self.enabled or self.model is None:
            return None

        try:
            # Prepare features
            features = self._extract_features(data)

            # Make prediction
            prediction = self.model.predict(features.reshape(1, -1))[0]
            probability = self.model.predict_proba(features.reshape(1, -1))[0]

            # Convert to signal
            if prediction == 1:  # Buy
                direction = "buy"
                strength = probability[1] * self.weight
            elif prediction == -1:  # Sell
                direction = "sell"
                strength = probability[0] * self.weight
            else:
                direction = "hold"
                strength = 0.0

            return Signal(
                strategy=self.name,
                symbol=symbol,
                direction=direction,
                strength=strength,
                timestamp=datetime.now(),
                metadata={"prediction": int(prediction), "confidence": max(probability)}
            )
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return None

    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features for ML model"""
        seq_len = self.parameters.get("sequence_length", 60)

        # Technical indicators
        returns = data["close"].pct_change().dropna()

        features = []

        # Price-based features
        features.append(data["close"].iloc[-1] / data["close"].iloc[-seq_len:].mean())
        features.append(returns.tail(5).mean())
        features.append(returns.tail(20).std())

        # Volume features
        features.append(data["volume"].iloc[-1] / data["volume"].tail(20).mean())

        # Trend features
        features.append((data["close"].iloc[-1] - data["close"].iloc[-20]) / data["close"].iloc[-20])

        return np.array(features)

class StrategyEngine:
    """Main engine that manages and coordinates all strategies"""

    def __init__(self):
        self.strategies: Dict[str, StrategyBase] = {}
        self.signals: List[Signal] = []
        self.executor = ThreadPoolExecutor(max_workers=CURRENT_HARDWARE["parallel_workers"])
        self._init_strategies()

    def _init_strategies(self):
        """Initialize all configured strategies"""
        strategy_map = {
            "momentum": MomentumStrategy,
            "mean_reversion": MeanReversionStrategy,
            "breakout": BreakoutStrategy,
            "ml_ensemble": MLEnsembleStrategy
        }

        for name, config in STRATEGIES.items():
            if name in strategy_map and config.get("enabled", False):
                self.strategies[name] = strategy_map[name](name, config)
                logger.info(f"Initialized strategy: {name}")

    async def analyze_symbol(self, symbol: str, data: pd.DataFrame) -> List[Signal]:
        """Run all strategies on a symbol and collect signals"""
        signals = []

        # Run strategies concurrently
        tasks = [
            strategy.analyze(symbol, data)
            for strategy in self.strategies.values()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Signal):
                signals.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Strategy error: {result}")

        self.signals = signals
        return signals

    def combine_signals(self, signals: List[Signal]) -> Optional[Signal]:
        """Combine multiple signals into consensus signal"""
        if not signals:
            return None

        # Filter by direction
        buy_signals = [s for s in signals if s.direction == "buy"]
        sell_signals = [s for s in signals if s.direction == "sell"]

        # Calculate weighted consensus
        buy_strength = sum(s.strength for s in buy_signals)
        sell_strength = sum(s.strength for s in sell_signals)

        # Determine consensus
        if buy_strength > sell_strength and buy_strength > 0.3:
            return Signal(
                strategy="consensus",
                symbol=signals[0].symbol,
                direction="buy",
                strength=buy_strength,
                timestamp=datetime.now(),
                metadata={
                    "buy_strategies": [s.strategy for s in buy_signals],
                    "sell_strategies": [s.strategy for s in sell_signals],
                    "consensus": buy_strength / (buy_strength + sell_strength)
                }
            )
        elif sell_strength > buy_strength and sell_strength > 0.3:
            return Signal(
                strategy="consensus",
                symbol=signals[0].symbol,
                direction="sell",
                strength=sell_strength,
                timestamp=datetime.now(),
                metadata={
                    "buy_strategies": [s.strategy for s in buy_signals],
                    "sell_strategies": [s.strategy for s in sell_signals],
                    "consensus": sell_strength / (buy_strength + sell_strength)
                }
            )
        else:
            return Signal(
                strategy="consensus",
                symbol=signals[0].symbol,
                direction="hold",
                strength=0.0,
                timestamp=datetime.now(),
                metadata={"reason": "no_clear_consensus"}
            )

    def get_strategy_performance(self) -> Dict[str, Dict]:
        """Get performance metrics for all strategies"""
        return {
            name: strategy.get_performance()
            for name, strategy in self.strategies.items()
        }

    def enable_strategy(self, name: str):
        """Enable a strategy"""
        if name in self.strategies:
            self.strategies[name].enabled = True
            logger.info(f"Enabled strategy: {name}")

    def disable_strategy(self, name: str):
        """Disable a strategy"""
        if name in self.strategies:
            self.strategies[name].enabled = False
            logger.info(f"Disabled strategy: {name}")

    def update_strategy_weight(self, name: str, weight: float):
        """Update strategy weight"""
        if name in self.strategies:
            self.strategies[name].weight = max(0.0, min(1.0, weight))
            logger.info(f"Updated {name} weight to {weight}")
