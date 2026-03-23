"""
OmniBot v2.6 Sentinel - Enhanced Configuration
Includes aggressive trading modes and auto-update settings
"""

from enum import Enum
from dataclasses import dataclass

class TradingMode(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    HFT = "hft"
    SENTINEL = "sentinel"

@dataclass
class StrategyConfig:
    name: str
    enabled: bool = True
    weight: float = 0.20
    confidence_threshold: float = 0.75
    risk_per_trade: float = 0.05
    aggressive_confidence: float = 0.55
    hft_confidence: float = 0.48

class Settings:
    TRADING_MODE = TradingMode.AGGRESSIVE
    MAX_CONCURRENT_POSITIONS = 10
    MAX_DAILY_LOSS = 0.10
    AUTO_UPDATE_ENABLED = True
    UPDATE_ON_WEEKEND = True
    UPDATE_CHECK_INTERVAL_HOURS = 24
    AUTO_CLOSE_ENABLED = True
    AUTO_CLOSE_TIME = "16:00"
    AUTO_CLOSE_WEEKEND = True
    DASHBOARD_PORT = 8081
    DASHBOARD_PASSWORD = "admin"
    GITHUB_REPO = "3D-Magic/OmniBot-Testing"

    @classmethod
    def set_trading_mode(cls, mode):
        mode_map = {
            "conservative": TradingMode.CONSERVATIVE,
            "moderate": TradingMode.MODERATE,
            "aggressive": TradingMode.AGGRESSIVE,
            "hft": TradingMode.HFT,
            "sentinel": TradingMode.SENTINEL
        }
        cls.TRADING_MODE = mode_map.get(mode.lower(), TradingMode.AGGRESSIVE)
