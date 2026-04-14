"""
Trading Strategies Module for OMNIBOT
Various trading strategies: Scalping, Day Trading, Swing Trading, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    SCALPING = "scalping"
    DAY_TRADING = "day_trading"
    SWING_TRADING = "swing_trading"
    POSITION_TRADING = "position_trading"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"


class BaseStrategy:
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, description: str, risk_level: str):
        self.name = name
        self.description = description
        self.risk_level = risk_level  # low, medium, high
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate trading signal - override in subclasses"""
        raise NotImplementedError
    
    def get_required_data(self) -> Dict:
        """Get required data parameters"""
        return {
            'timeframe': '1d',
            'lookback': 50
        }


class ScalpingStrategy(BaseStrategy):
    """
    Scalping Strategy
    - Very short-term trades (minutes to hours)
    - Small profit targets (0.5% - 1%)
    - Tight stop losses (0.3% - 0.5%)
    - High frequency trading
    - Uses 1-minute to 5-minute candles
    """
    
    def __init__(self):
        super().__init__(
            name="Scalping",
            description="High-frequency short-term trades with small profit targets",
            risk_level="high"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '1m',  # 1-minute candles
            'lookback': 100
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate scalping signal using EMA cross and RSI"""
        if len(df) < 20:
            return None
        
        # Calculate indicators
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Buy signal: EMA 9 crosses above EMA 21 with RSI confirmation
        if (prev['ema_9'] <= prev['ema_21'] and 
            current['ema_9'] > current['ema_21'] and
            current['rsi'] > 40 and current['rsi'] < 70 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.7,
                'reason': f"EMA cross + RSI {current['rsi']:.1f}",
                'stop_loss_pct': 0.5,  # 0.5% stop
                'take_profit_pct': 1.0  # 1% target
            }
        
        # Sell signal
        if (prev['ema_9'] >= prev['ema_21'] and 
            current['ema_9'] < current['ema_21'] and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.7,
                'reason': f"EMA cross down + RSI {current['rsi']:.1f}"
            }
        
        return None


class DayTradingStrategy(BaseStrategy):
    """
    Day Trading Strategy
    - Intraday trades (open and close same day)
    - 1% - 3% profit targets
    - 1% - 2% stop losses
    - Uses 5-minute to 15-minute candles
    """
    
    def __init__(self):
        super().__init__(
            name="Day Trading",
            description="Intraday trades closed before market close",
            risk_level="medium"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '5m',  # 5-minute candles
            'lookback': 78  # One trading day
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate day trading signal using VWAP and Bollinger Bands"""
        if len(df) < 50:
            return None
        
        # VWAP
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (df['typical_price'] * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(20).mean()
        df['std_20'] = df['close'].rolling(20).std()
        df['upper_band'] = df['sma_20'] + (df['std_20'] * 2)
        df['lower_band'] = df['sma_20'] - (df['std_20'] * 2)
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        
        # Buy: Price above VWAP, near lower Bollinger Band, RSI > 40
        if (current['close'] > current['vwap'] and
            current['close'] < current['lower_band'] * 1.02 and
            current['rsi'] > 40 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.65,
                'reason': f"VWAP bounce + Lower BB + RSI {current['rsi']:.1f}",
                'stop_loss_pct': 1.5,
                'take_profit_pct': 3.0
            }
        
        # Sell: Price near upper Bollinger Band
        if (current['close'] > current['upper_band'] * 0.98 and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.65,
                'reason': f"Upper BB touch + RSI {current['rsi']:.1f}"
            }
        
        return None


class SwingTradingStrategy(BaseStrategy):
    """
    Swing Trading Strategy
    - Multi-day to multi-week holds
    - 5% - 10% profit targets
    - 3% - 5% stop losses
    - Uses daily candles
    """
    
    def __init__(self):
        super().__init__(
            name="Swing Trading",
            description="Multi-day holds capturing medium-term price movements",
            risk_level="medium"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '1d',  # Daily candles
            'lookback': 100
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate swing trading signal using MACD and SMA cross"""
        if len(df) < 50:
            return None
        
        # MACD
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # SMA
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Buy: MACD cross above signal, SMA 20 > SMA 50
        if (prev['macd'] <= prev['macd_signal'] and
            current['macd'] > current['macd_signal'] and
            current['sma_20'] > current['sma_50'] and
            current['rsi'] > 45 and current['rsi'] < 70 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.75,
                'reason': f"MACD cross + SMA trend + RSI {current['rsi']:.1f}",
                'stop_loss_pct': 4.0,
                'take_profit_pct': 8.0
            }
        
        # Sell: MACD cross below signal
        if (prev['macd'] >= prev['macd_signal'] and
            current['macd'] < current['macd_signal'] and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.75,
                'reason': f"MACD cross down + RSI {current['rsi']:.1f}"
            }
        
        return None


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy
    - Ride strong price trends
    - 8% - 15% profit targets
    - 5% - 8% stop losses (trailing)
    - Uses daily candles with volume
    """
    
    def __init__(self):
        super().__init__(
            name="Momentum",
            description="Ride strong price trends with volume confirmation",
            risk_level="high"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '1d',
            'lookback': 50
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate momentum signal using price rate of change and volume"""
        if len(df) < 20:
            return None
        
        # Rate of Change (10-day)
        df['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
        
        # Volume SMA
        df['volume_sma'] = df['volume'].rolling(20).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        
        # Buy: Strong momentum (ROC > 5%), high volume, RSI in sweet spot
        if (current['roc_10'] > 5 and
            current['volume'] > current['volume_sma'] * 1.2 and
            current['rsi'] > 50 and current['rsi'] < 75 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.7,
                'reason': f"Momentum ROC {current['roc_10']:.1f}% + Volume spike + RSI {current['rsi']:.1f}",
                'stop_loss_pct': 6.0,
                'take_profit_pct': 12.0
            }
        
        # Sell: Momentum fading
        if (current['roc_10'] < 0 and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.7,
                'reason': f"Momentum fading ROC {current['roc_10']:.1f}%"
            }
        
        return None


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy
    - Trade price reversions to mean
    - 3% - 6% profit targets
    - 2% - 4% stop losses
    - Uses daily candles
    """
    
    def __init__(self):
        super().__init__(
            name="Mean Reversion",
            description="Trade price reversions back to moving average",
            risk_level="medium"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '1d',
            'lookback': 50
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate mean reversion signal using Bollinger Bands"""
        if len(df) < 20:
            return None
        
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(20).mean()
        df['std_20'] = df['close'].rolling(20).std()
        df['upper_band'] = df['sma_20'] + (df['std_20'] * 2)
        df['lower_band'] = df['sma_20'] - (df['std_20'] * 2)
        df['bb_position'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        
        # Buy: Price below lower band (oversold), RSI < 30
        if (current['close'] < current['lower_band'] and
            current['rsi'] < 35 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.7,
                'reason': f"Oversold BB {current['bb_position']:.2f} + RSI {current['rsi']:.1f}",
                'stop_loss_pct': 3.0,
                'take_profit_pct': 5.0
            }
        
        # Sell: Price above upper band (overbought)
        if (current['close'] > current['upper_band'] and
            current['rsi'] > 65 and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.7,
                'reason': f"Overbought BB {current['bb_position']:.2f} + RSI {current['rsi']:.1f}"
            }
        
        return None


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy
    - Trade price breakouts from consolidation
    - 10% - 20% profit targets
    - 5% - 8% stop losses
    - Uses daily candles
    """
    
    def __init__(self):
        super().__init__(
            name="Breakout",
            description="Trade breakouts from support/resistance levels",
            risk_level="high"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '1d',
            'lookback': 100
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate breakout signal using support/resistance levels"""
        if len(df) < 50:
            return None
        
        # Calculate support and resistance (20-day high/low)
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()
        
        # Volume average
        df['volume_sma'] = df['volume'].rolling(20).mean()
        
        # ATR for volatility
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Buy: Break above resistance with volume
        if (prev['close'] <= prev['resistance'] and
            current['close'] > current['resistance'] and
            current['volume'] > current['volume_sma'] * 1.5 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.75,
                'reason': f"Breakout above ${current['resistance']:.2f} with volume",
                'stop_loss_pct': 5.0,
                'take_profit_pct': 15.0
            }
        
        # Sell: Break below support
        if (prev['close'] >= prev['support'] and
            current['close'] < current['support'] and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.75,
                'reason': f"Breakdown below ${current['support']:.2f}"
            }
        
        return None


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy
    - Follow established trends
    - 10% - 20% profit targets
    - Use trailing stops
    - Uses daily candles
    """
    
    def __init__(self):
        super().__init__(
            name="Trend Following",
            description="Follow established price trends with trailing stops",
            risk_level="medium"
        )
    
    def get_required_data(self) -> Dict:
        return {
            'timeframe': '1d',
            'lookback': 100
        }
    
    def generate_signal(self, df: pd.DataFrame, symbol: str, has_position: bool) -> Optional[Dict]:
        """Generate trend following signal using ADX and moving averages"""
        if len(df) < 50:
            return None
        
        # Moving averages
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        
        # ADX calculation (simplified)
        df['plus_dm'] = df['high'].diff()
        df['minus_dm'] = -df['low'].diff()
        df['plus_dm'] = df['plus_dm'].where(df['plus_dm'] > df['minus_dm'], 0)
        df['minus_dm'] = df['minus_dm'].where(df['minus_dm'] > df['plus_dm'], 0)
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        
        # Buy: Golden cross (SMA 50 > SMA 200), uptrend
        if (current['sma_50'] > current['sma_200'] and
            current['close'] > current['sma_50'] and
            current['rsi'] > 50 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': 'buy',
                'confidence': 0.75,
                'reason': f"Uptrend SMA50>SMA200 + RSI {current['rsi']:.1f}",
                'stop_loss_pct': 6.0,
                'take_profit_pct': 15.0,
                'use_trailing_stop': True
            }
        
        # Sell: Death cross or close below SMA 50
        if (current['close'] < current['sma_50'] and
            has_position):
            
            return {
                'symbol': symbol,
                'side': 'sell',
                'confidence': 0.75,
                'reason': f"Trend reversal - below SMA50"
            }
        
        return None


# Strategy registry
STRATEGIES = {
    'scalping': ScalpingStrategy(),
    'day_trading': DayTradingStrategy(),
    'swing_trading': SwingTradingStrategy(),
    'momentum': MomentumStrategy(),
    'mean_reversion': MeanReversionStrategy(),
    'breakout': BreakoutStrategy(),
    'trend_following': TrendFollowingStrategy()
}


def get_strategy(name: str) -> Optional[BaseStrategy]:
    """Get a strategy by name"""
    return STRATEGIES.get(name.lower().replace(' ', '_'))


def get_all_strategies() -> Dict:
    """Get all available strategies with their info"""
    return {
        key: {
            'name': strategy.name,
            'description': strategy.description,
            'risk_level': strategy.risk_level,
            'timeframe': strategy.get_required_data()['timeframe']
        }
        for key, strategy in STRATEGIES.items()
    }
