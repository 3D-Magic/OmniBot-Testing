"""
OMNIBOT v2.7 Titan - Configuration
Multi-Market Trading: Stocks + Crypto + Forex
24/7 Remote Access via Multiple Tunnel Options
"""

import os
from pathlib import Path
from typing import Dict, List

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
HISTORY_DIR = DATA_DIR / "history"
BACKUPS_DIR = BASE_DIR / "backups"
UPDATES_DIR = BASE_DIR / "updates"

# Create directories
for dir_path in [DATA_DIR, CACHE_DIR, LOGS_DIR, HISTORY_DIR, BACKUPS_DIR, UPDATES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Version info
VERSION = "2.7.0"
VERSION_NAME = "Titan"
BUILD_DATE = "2026-03-26"

# ═══════════════════════════════════════════════════════════
# TRADING MODES (from v2.6.1 Sentinel)
# ═══════════════════════════════════════════════════════════

TRADING_MODES = {
    "conservative": {
        "risk_per_trade": 0.01,
        "max_positions": 5,
        "leverage": 1.0,
        "stop_loss_atr": 2.0,
        "take_profit_atr": 4.0,
        "description": "Low risk, steady growth - Best for beginners"
    },
    "moderate": {
        "risk_per_trade": 0.02,
        "max_positions": 10,
        "leverage": 1.0,
        "stop_loss_atr": 1.5,
        "take_profit_atr": 3.0,
        "description": "Balanced risk/reward - Recommended for most users"
    },
    "aggressive": {
        "risk_per_trade": 0.05,
        "max_positions": 15,
        "leverage": 2.0,
        "stop_loss_atr": 1.0,
        "take_profit_atr": 2.0,
        "description": "High risk, high reward - For experienced traders"
    },
    "hft_scalper": {
        "risk_per_trade": 0.02,
        "max_positions": 20,
        "leverage": 3.0,
        "stop_loss_atr": 0.5,
        "take_profit_atr": 1.0,
        "hold_time_minutes": 5,
        "description": "High frequency scalping - Many small trades"
    },
    "sentinel": {
        "risk_per_trade": 0.025,
        "max_positions": 12,
        "leverage": 1.5,
        "stop_loss_atr": 1.2,
        "take_profit_atr": 2.5,
        "ai_override": True,
        "description": "AI-enhanced with override - Smart adaptive trading"
    }
}

# Current trading mode
ACTIVE_MODE = "moderate"

# ═══════════════════════════════════════════════════════════
# REMOTE ACCESS OPTIONS (No Port Forwarding Needed)
# ═══════════════════════════════════════════════════════════

REMOTE_ACCESS = {
    "primary_method": "tailscale",  # Options: tailscale, cloudflare, ngrok, localhost_run
    "domain": "",  # Your custom domain (if using Cloudflare)
    "static_url": ""  # Your static URL (if available)
}

# ═══════════════════════════════════════════════════════════
# MARKET API CONFIGURATIONS
# ═══════════════════════════════════════════════════════════

# 1. ALPACA - US Stocks & ETFs
# Signup: https://alpaca.markets
# Free paper trading with $100k virtual money
ALPACA = {
    "api_key": os.getenv("ALPACA_API_KEY", ""),
    "secret_key": os.getenv("ALPACA_SECRET_KEY", ""),
    "paper": True,
    "base_url": "https://paper-api.alpaca.markets",
    "enabled": True,
    "market_hours": {
        "pre_market": "04:00",
        "regular": "09:30",
        "after_hours": "16:00",
        "close": "20:00"
    }
}

# 2. CRYPTO - CCXT supports 100+ exchanges
# BINANCE: https://www.binance.com/en/my/settings/api-management
# COINBASE: https://www.coinbase.com/settings/api
# KRAKEN: https://www.kraken.com/u/security/api
CRYPTO = {
    "enabled": False,
    "exchange": "binance",  # binance, coinbase, kraken, kucoin, etc.
    "api_key": os.getenv("CRYPTO_API_KEY", ""),
    "secret": os.getenv("CRYPTO_SECRET", ""),
    "testnet": True,  # Use testnet first!
    "sandbox": True,
    "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
    "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
}

# 3. FOREX - OANDA (Recommended for beginners)
# Signup: https://www.oanda.com/demo-account/
# API Docs: https://developer.oanda.com/
FOREX = {
    "enabled": False,
    "account_id": os.getenv("OANDA_ACCOUNT_ID", ""),
    "access_token": os.getenv("OANDA_ACCESS_TOKEN", ""),
    "environment": "practice",  # "practice" or "live"
    "base_url": "https://api-fxpractice.oanda.com",
    "instruments": [
        "EUR_USD",  # Euro / US Dollar
        "GBP_USD",  # British Pound / US Dollar
        "USD_JPY",  # US Dollar / Japanese Yen
        "AUD_USD",  # Australian Dollar / US Dollar
        "USD_CAD",  # US Dollar / Canadian Dollar
        "EUR_GBP",  # Euro / British Pound
        "EUR_JPY",  # Euro / Japanese Yen
        "GBP_JPY",  # British Pound / Japanese Yen
        "XAU_USD",  # Gold
        "XAG_USD"   # Silver
    ],
    "default_units": 1000  # Micro lots for testing
}

# 4. OPTIONS (Alpaca supports options trading)
OPTIONS = {
    "enabled": False,
    "provider": "alpaca",  # Currently only Alpaca supported
    "max_delta": 0.30,     # Max 30 delta for risk management
    "min_dte": 7,          # Minimum days to expiration
    "max_dte": 45          # Maximum days to expiration
}

# ═══════════════════════════════════════════════════════════
# TRADING SETTINGS
# ═══════════════════════════════════════════════════════════

TRADING = {
    "mode": "paper",  # "paper" or "live"
    "active_mode": ACTIVE_MODE,
    "max_positions": TRADING_MODES[ACTIVE_MODE]["max_positions"],
    "risk_per_trade": TRADING_MODES[ACTIVE_MODE]["risk_per_trade"],
    "max_daily_loss": 0.05,
    "paper_balance": 10000.0,
    "market_hours_only": False,  # Set True for stocks only
    "auto_start": False,
    "emergency_stop_loss": 0.10,  # Stop all trading if down 10%
    "watchlist": {
        "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "NFLX"],
        "crypto": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT"],
        "forex": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "XAU_USD"]
    }
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
    "auth_required": True,
    "password": os.getenv("OMNIBOT_PASSWORD", "admin"),
    "max_login_attempts": 3,
    "session_timeout": 3600,
    "allow_unsafe_werkzeug": True,
    "theme": "dark",
    "refresh_interval": 5  # Seconds
}

# Auto-updater settings
AUTO_UPDATER = {
    "enabled": True,
    "check_interval_hours": 24,
    "auto_install": True,
    "backup_before_update": True,
    "update_on_weekend": True,
    "update_time": "02:00",
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
    "sources": ["reddit", "rss", "twitter"],
    "reddit_subreddits": ["wallstreetbets", "stocks", "investing", "cryptocurrency", "forex"],
    "rss_feeds": [
        "https://finance.yahoo.com/news/rssindex",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://www.forexlive.com/feed/news"
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
    "hardware_profile": "auto",
    "max_workers": 4,
    "use_gpu": False,
    "memory_limit_mb": 8192
}
