"""
Configuration Constants
"""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

# Settings file
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')

# Default settings
DEFAULT_SETTINGS = {
    # Dashboard settings
    'dashboard_host': '0.0.0.0',
    'dashboard_port': 8081,
    'password': 'admin',
    
    # Trading settings
    'trading_enabled': False,
    'trading_mode': 'paper',  # 'paper' or 'live'
    'strategy': 'swing_trading',  # 'scalping', 'day_trading', 'swing_trading', 'momentum', 'mean_reversion', 'breakout', 'trend_following'
    
    # Risk management
    'stop_loss_pct': 5.0,
    'take_profit_pct': 10.0,
    'max_position_pct': 10.0,
    'max_daily_loss_pct': 5.0,
    'enable_stop_loss': True,
    'enable_take_profit': True,
    'enable_trailing': False,
    
    # Watchlists
    'alpaca_watchlist': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX'],
    'binance_watchlist': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
    
    # Screen settings (Raspberry Pi)
    'screen_brightness': 100,
    'screen_sleep_enabled': True,
    'screen_sleep_seconds': 600,  # 10 minutes
    
    # Security settings
    'login_on_wake': True,
    'auto_logout': True,
    
    # System settings
    'auto_start': False,
    'email_notifications': False,
    'debug_mode': False,
    
    # Broker settings (will be populated from dashboard)
    'alpaca': {
        'enabled': False,
        'paper': True,
        'api_key': '',
        'secret_key': ''
    },
    'binance': {
        'enabled': False,
        'testnet': True,
        'api_key': '',
        'secret_key': ''
    },
    'paypal': {
        'enabled': False,
        'sandbox': True,
        'client_id': '',
        'client_secret': ''
    },
    'interactive_brokers': {
        'enabled': False,
        'host': '127.0.0.1',
        'port': 7497,
        'client_id': 1
    }
}
