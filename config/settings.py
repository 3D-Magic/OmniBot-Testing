"""
OMNIBOT v2.7 Titan - Configuration
Edit this file with your API keys or use: python src/main.py --setup
"""

import os
from enum import Enum

# Version
VERSION = "v2.7.0-titan"

# === TRADING MODES ===
class TradingMode(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    HFT = "hft"
    SENTINEL = "sentinel"

# === ALPACA (Stocks) - REQUIRED ===
ALPACA = {
    "api_key": os.getenv("ALPACA_API_KEY", "YOUR_ALPACA_API_KEY_HERE"),
    "secret_key": os.getenv("ALPACA_SECRET_KEY", "YOUR_ALPACA_SECRET_KEY_HERE"),
    "paper": True,  # Set to False for live trading
    "base_url": "https://paper-api.alpaca.markets",
    "enabled": True
}

# === CRYPTO (Binance/others) - OPTIONAL ===
CRYPTO = {
    "enabled": False,  # Set to True to enable crypto trading
    "exchange": "binance",  # binance, coinbase, kraken, kucoin, etc.
    "api_key": os.getenv("CRYPTO_API_KEY", "YOUR_CRYPTO_API_KEY_HERE"),
    "secret": os.getenv("CRYPTO_SECRET", "YOUR_CRYPTO_SECRET_HERE"),
    "testnet": True,  # Use testnet first!
    "sandbox": True,
    "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]
}

# === FOREX (OANDA) - OPTIONAL ===
FOREX = {
    "enabled": False,  # Set to True to enable forex trading
    "account_id": os.getenv("OANDA_ACCOUNT_ID", "YOUR_OANDA_ACCOUNT_ID"),
    "access_token": os.getenv("OANDA_ACCESS_TOKEN", "YOUR_OANDA_ACCESS_TOKEN"),
    "environment": "practice",  # "practice" or "live"
    "base_url": "https://api-fxpractice.oanda.com",
    "symbols": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]
}

# === TRADING SETTINGS ===
TRADING = {
    "mode": TradingMode.MODERATE,
    "initial_capital": 10000.0,
    "risk_per_trade": 0.02,  # 2% risk per trade
    "max_positions": 10,
    "watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"],
    "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
}

# === AUTO-UPDATER ===
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

# === EXTERNAL ACCESS ===
EXTERNAL_ACCESS = {
    "enabled": True,
    "use_ngrok": False,
    "use_tailscale": True,
    "use_cloudflare": False,
    "custom_domain": None
}

# === DASHBOARD ===
DASHBOARD = {
    "host": "0.0.0.0",
    "port": 8081,
    "password": "admin",  # Change with: python src/main.py --change-password
    "debug": False
}