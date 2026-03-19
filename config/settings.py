"""
OMNIBOT v2.6 Sentinel - Configuration
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
UPDATES_DIR = BASE_DIR / "updates"

# Create directories
for dir_path in [DATA_DIR, CACHE_DIR, LOGS_DIR, BACKUPS_DIR, UPDATES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Version info
VERSION = "2.6.0"
VERSION_NAME = "Sentinel"
BUILD_DATE = "2026-03-19"

# Trading settings
TRADING = {
    "mode": "paper",  # paper or live
    "max_positions": 10,
    "risk_per_trade": 0.02,
    "max_daily_loss": 0.05,
    "paper_balance": 10000.0,
    "watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"],
    "market_hours_only": True,
    "auto_start": False
}

# Strategy settings
STRATEGIES = {
    "momentum": {"enabled": True, "weight": 0.25, "lookback": 20},
    "mean_reversion": {"enabled": True, "weight": 0.25, "z_threshold": 2.0},
    "breakout": {"enabled": True, "weight": 0.25, "atr_period": 14},
    "ml_ensemble": {"enabled": True, "weight": 0.25, "model_type": "sklearn"}
}

# Dashboard settings
DASHBOARD = {
    "enabled": True,
    "port": 8081,
    "host": "0.0.0.0",
    "debug": False,
    "auth_required": True,  # Fixed: Added this key
    "password": "admin",  # Change this!
    "max_login_attempts": 3,
    "session_timeout": 3600,
    "allow_unsafe_werkzeug": True  # Fixed: Added for ngrok/external access
}

# External Access / ngrok settings
EXTERNAL_ACCESS = {
    "enabled": False,
    "ngrok_token": "",  # Set this via --setup
    "ngrok_region": "us",
    "ngrok_auth": None,
    "keep_terminal_alive": True,
    "auto_restart": True
}

# Auto-updater settings
AUTO_UPDATER = {
    "enabled": True,
    "check_interval_hours": 24,
    "auto_install": True,
    "backup_before_update": True,
    "update_on_weekend": True,  # Only update when market is closed
    "update_time": "02:00",  # 2 AM local time
    "rollback_on_failure": True,
    "version_url": "https://api.github.com/repos/3D-Magic/OmniBot-Testing/releases/latest",
    "repo_url": "https://github.com/3D-Magic/OmniBot-Testing.git"
}

# Data sources
DATA_SOURCES = {
    "primary": "yfinance",
    "fallback": "ccxt",
    "cache_enabled": True,
    "cache_duration_minutes": 15
}

# Sentiment analysis
SENTIMENT = {
    "enabled": True,
    "sources": ["reddit", "rss"],
    "reddit_subreddits": ["wallstreetbets", "stocks", "investing"],
    "rss_feeds": [
        "https://finance.yahoo.com/news/rssindex",
        "https://feeds.marketwatch.com/marketwatch/topstories/"
    ],
    "update_interval_minutes": 30,
    "min_mentions": 5
}

# Logging
LOGGING = {
    "level": "INFO",
    "max_file_size_mb": 10,
    "max_files": 5,
    "console_output": True
}

# Performance
PERFORMANCE = {
    "hardware_profile": "auto",  # auto, pi5_8gb, pi4_8gb, pi4_4gb
    "max_workers": 2,
    "use_gpu": False,
    "memory_limit_mb": 4096
}
