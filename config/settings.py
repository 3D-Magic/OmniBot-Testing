"""
OMNIBOT v2.6 Sentinel - Configuration
Version: 2.6.0
Codename: Sentinel
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
BACKTEST_DIR = DATA_DIR / "backtests"

# Version info
VERSION = "2.6.0"
VERSION_NAME = "Sentinel"
MINOR_VERSION = "2.6"
BUILD_DATE = "2026-03-19"

# Hardware settings (Pi 5 8GB optimized, Pi 4 compatible)
HARDWARE = {
    "pi5_8gb": {
        "max_strategies": 4,
        "ml_model_size": "large",
        "cache_size_mb": 2048,
        "parallel_workers": 4,
        "dashboard_enabled": True
    },
    "pi4_4gb": {
        "max_strategies": 1,
        "ml_model_size": "small",
        "cache_size_mb": 512,
        "parallel_workers": 2,
        "dashboard_enabled": True
    },
    "pi4_8gb": {
        "max_strategies": 2,
        "ml_model_size": "medium",
        "cache_size_mb": 1024,
        "parallel_workers": 3,
        "dashboard_enabled": True
    }
}

# Auto-detect hardware
def detect_hardware():
    """Detect Raspberry Pi hardware capabilities"""
    try:
        with open("/proc/meminfo", "r") as f:
            mem_info = f.read()

        # Parse total memory
        for line in mem_info.split("\n"):
            if "MemTotal" in line:
                mem_kb = int(line.split()[1])
                mem_gb = mem_kb / (1024 * 1024)
                break

        # Check for Pi 5 (has different CPU info)
        with open("/proc/cpuinfo", "r") as f:
            cpu_info = f.read()

        if "BCM2712" in cpu_info or "Cortex-A76" in cpu_info:
            return "pi5_8gb" if mem_gb >= 6 else "pi5_4gb"
        else:
            return "pi4_8gb" if mem_gb >= 6 else "pi4_4gb"
    except:
        return "pi4_4gb"  # Safe fallback

HARDWARE_PROFILE = detect_hardware()
CURRENT_HARDWARE = HARDWARE[HARDWARE_PROFILE]

# Trading settings
TRADING = {
    "mode": "paper",  # paper, live
    "default_exchange": "alpaca",
    "max_positions": 10,
    "risk_per_trade": 0.02,  # 2% per trade
    "max_daily_loss": 0.05,  # 5% max daily loss
    "position_sizing": "kelly",  # kelly, fixed, percent
    "rebalance_interval": 86400,  # Daily in seconds
}

# Exchange settings (FREE tiers only)
EXCHANGES = {
    "alpaca": {
        "enabled": True,
        "paper_url": "https://paper-api.alpaca.markets",
        "live_url": "https://api.alpaca.markets",
        "rate_limit": 200,  # requests per minute
        "free_tier": True
    },
    "yahoo": {
        "enabled": True,
        "url": "https://query1.finance.yahoo.com",
        "rate_limit": 2000,
        "free_tier": True
    }
}

# Strategy settings
STRATEGIES = {
    "momentum": {
        "enabled": True,
        "weight": 0.25,
        "timeframe": "1d",
        "parameters": {
            "lookback": 20,
            "threshold": 0.05
        }
    },
    "mean_reversion": {
        "enabled": True,
        "weight": 0.25,
        "timeframe": "1d",
        "parameters": {
            "z_score_threshold": 2.0,
            "lookback": 30
        }
    },
    "breakout": {
        "enabled": True,
        "weight": 0.25,
        "timeframe": "1d",
        "parameters": {
            "atr_period": 14,
            "breakout_factor": 1.5
        }
    },
    "ml_ensemble": {
        "enabled": True,
        "weight": 0.25,
        "timeframe": "1d",
        "parameters": {
            "model_type": "lstm",
            "sequence_length": 60,
            "prediction_horizon": 5
        }
    }
}

# Sentiment analysis (FREE sources only)
SENTIMENT = {
    "enabled": True,
    "sources": {
        "reddit": {
            "enabled": True,
            "subreddits": ["wallstreetbets", "stocks", "investing", "stockmarket"],
            "refresh_interval": 300,  # 5 minutes
            "free_tier": True
        },
        "rss": {
            "enabled": True,
            "feeds": [
                "https://finance.yahoo.com/news/rssindex",
                "https://feeds.marketwatch.com/marketwatch/topstories",
                "https://seekingalpha.com/feed.xml"
            ],
            "refresh_interval": 600,  # 10 minutes
            "free_tier": True
        },
        "twitter": {
            "enabled": False,  # Optional - requires API keys
            "free_tier": True,  # Twitter API v2 free tier
            "refresh_interval": 900  # 15 minutes (rate limited)
        }
    },
    "sentiment_threshold": 0.2,  # Minimum sentiment to act on
    "impact_weight": 0.15  # Weight in trading decisions
}

# Dashboard settings
DASHBOARD = {
    "enabled": CURRENT_HARDWARE["dashboard_enabled"],
    "host": "0.0.0.0",
    "port": 8080,
    "refresh_interval": 5000,  # ms
    "theme": "dark",
    "auth_required": True,
    "mobile_optimized": True
}

# Backtesting settings
BACKTEST = {
    "default_start_date": "2023-01-01",
    "default_end_date": "2024-12-31",
    "initial_capital": 100000,
    "commission": 0.001,  # 0.1%
    "slippage": 0.0005,  # 0.05%
    "parallel_jobs": CURRENT_HARDWARE["parallel_workers"]
}

# Weekend auto-update settings (from v2.5.1 memory)
AUTO_UPDATE = {
    "enabled": True,
    "check_interval": 3600,  # Check every hour
    "update_window": {
        "day": "saturday",  # Or "sunday"
        "time": "02:00"     # 2 AM
    },
    "backup_before_update": True,
    "rollback_on_failure": True,
    "sources": ["github", "official"]
}

# Logging
LOGGING = {
    "level": "INFO",
    "max_file_size_mb": 50,
    "backup_count": 5,
    "console_output": True,
    "file_output": True
}

# Security (maintained from v2.5)
SECURITY = {
    "integrity_check": True,
    "admin_password_required": True,
    "encrypted_config": True,
    "max_login_attempts": 3,
    "lockout_duration": 3600  # 1 hour
}

# Notification settings (FREE options)
NOTIFICATIONS = {
    "email": {
        "enabled": False,
        "smtp_server": "",
        "smtp_port": 587,
        "username": "",
        "password": ""
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "discord": {
        "enabled": False,
        "webhook_url": ""
    }
}
