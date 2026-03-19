"""
OMNIBOT v2.6 Sentinel - Configuration
All settings centralized here
"""

import os
from pathlib import Path

# Version
VERSION = "2.6.0"
VERSION_NAME = "Sentinel"

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
UPDATES_DIR = BASE_DIR / "updates"

# Hardware Detection (auto-detect on startup)
HARDWARE = {
    "profile": "auto",  # auto, pi5_8gb, pi4_8gb, pi4_4gb, desktop
    "max_strategies": 4,
    "max_workers": 2,
    "ml_model_size": "large",  # large, medium, small
    "enable_gpu": False,
    "cache_size_mb": 512
}

# Trading Settings
TRADING = {
    "mode": "paper",  # paper or live
    "max_positions": 10,
    "risk_per_trade": 0.02,  # 2% per trade
    "max_daily_loss": 0.05,  # Stop after 5% loss
    "max_weekly_loss": 0.10,  # Stop after 10% weekly loss
    "default_qty": 10,
    "min_position_size": 1,
    "max_position_size": 1000,
    "paper_capital": 100000.0,
    "live_capital": 0.0,  # Set during setup
}

# Watchlist - Default symbols
WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "NFLX", "AMD", "INTC",
    "TQQQ", "SOXL", "SPY", "QQQ", "IWM"
]

# Strategy Configuration
STRATEGIES = {
    "momentum": {
        "enabled": True,
        "weight": 0.25,
        "params": {
            "lookback": 20,
            "threshold": 0.05
        }
    },
    "mean_reversion": {
        "enabled": True,
        "weight": 0.25,
        "params": {
            "z_score_threshold": 2.0,
            "lookback": 20
        }
    },
    "breakout": {
        "enabled": True,
        "weight": 0.25,
        "params": {
            "atr_period": 14,
            "breakout_factor": 1.5
        }
    },
    "ml_ensemble": {
        "enabled": True,
        "weight": 0.25,
        "params": {
            "sequence_length": 60,
            "prediction_horizon": 5,
            "confidence_threshold": 0.6
        }
    }
}

# API Configuration (encrypted during setup)
API = {
    "alpaca_key": "",
    "alpaca_secret": "",
    "alpaca_paper_url": "https://paper-api.alpaca.markets",
    "alpaca_live_url": "https://api.alpaca.markets",
    "reddit_client_id": "",
    "reddit_client_secret": "",
    "reddit_user_agent": "OMNIBOT-Sentinel/2.6.0"
}

# Dashboard Settings
DASHBOARD = {
    "enabled": True,
    "host": "0.0.0.0",
    "port": 8080,
    "debug": False,
    "password": "admin",  # CHANGE THIS!
    "refresh_interval": 10,  # seconds
    "theme": "dark",
    "allow_unsafe_werkzeug": True  # Required for ngrok/external access
}

# Sentiment Analysis
SENTIMENT = {
    "enabled": True,
    "sources": ["reddit", "rss"],
    "reddit_subreddits": ["wallstreetbets", "stocks", "investing", "stockmarket"],
    "rss_feeds": [
        "https://feeds.finance.yahoo.com/rss/2.0/headlines?s={symbol}",
        "https://www.marketwatch.com/rss/marketwatch"
    ],
    "update_interval": 300,  # 5 minutes
    "min_mentions": 5,
    "sentiment_threshold": 0.2
}

# Auto-Update Settings
AUTO_UPDATE = {
    "enabled": True,
    "check_interval_hours": 24,
    "auto_install": True,
    "backup_before_update": True,
    "rollback_on_failure": True,
    "update_url": "https://api.github.com/repos/3D-Magic/OmniBot/releases/latest",
    "allowed_days": ["Saturday", "Sunday"],  # Only update on weekends
    "allowed_hours": [0, 1, 2, 3, 4, 5, 22, 23]  # Only during off-market hours
}

# Logging
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "max_file_size_mb": 10,
    "backup_count": 5,
    "log_to_console": True,
    "log_to_file": True
}

# Risk Management
RISK = {
    "max_correlation": 0.7,  # Max correlation between positions
    "sector_limits": {
        "technology": 0.30,
        "healthcare": 0.20,
        "finance": 0.20,
        "energy": 0.10,
        "other": 0.20
    },
    "volatility_adjustment": True,
    "stop_loss_enabled": True,
    "default_stop_loss": 0.05,  # 5% stop loss
    "trailing_stop_enabled": False,
    "trailing_stop_pct": 0.10
}

# Backtesting
BACKTEST = {
    "default_start": "2023-01-01",
    "default_end": "2024-01-01",
    "commission": 0.001,  # 0.1% per trade
    "slippage": 0.001,  # 0.1% slippage
    "initial_capital": 100000.0
}

# External Access / ngrok
EXTERNAL_ACCESS = {
    "enabled": False,  # Set to True to enable ngrok on startup
    "ngrok_authtoken": "",  # Your ngrok authtoken
    "ngrok_region": "us",  # us, eu, ap, au, sa, jp, in
    "ngrok_subdomain": "",  # Leave empty for random
    "dashboard_port": 8080,
    "keep_terminal_alive": True  # Keep terminal session alive for ngrok
}

def get_alpaca_credentials():
    """Get Alpaca API credentials"""
    return {
        "api_key": API["alpaca_key"],
        "api_secret": API["alpaca_secret"],
        "base_url": API["alpaca_paper_url"] if TRADING["mode"] == "paper" else API["alpaca_live_url"]
    }

def is_market_hours():
    """Check if US market is open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    from datetime import datetime
    import pytz

    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)

    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now <= market_close
