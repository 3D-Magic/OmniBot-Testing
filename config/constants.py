"""
OMNIBOT Constants
"""

# File paths
SETTINGS_FILE = '/etc/omnibot/settings.json'

# Default settings
DEFAULT_SETTINGS = {
    'version': 'v2.7.2-titan',
    'password': 'admin',
    'alpaca_key': '',
    'alpaca_secret': '',
    'binance_key': '',
    'binance_secret': '',
    'ig_api_key': '',
    'ig_username': '',
    'ig_password': '',
    'ig_account_id': '',
    'ibkr_account_id': '',
    'ibkr_username': '',
    'ibkr_password': '',
    'paypal_client_id': '',
    'paypal_client_secret': '',
    'trading_mode': 'demo',
    'strategy': 'moderate',
    'screen_brightness': 200,
    'trading_enabled': False
}

# Trading constants
TRADING_STRATEGIES = ['conservative', 'moderate', 'aggressive']
DEFAULT_CAPITAL = 100000.0

# Broker types
BROKER_ALPACA = 'alpaca'
BROKER_BINANCE = 'binance'
BROKER_IG = 'ig'
BROKER_IBKR = 'ibkr'
BROKER_PAYPAL = 'paypal'
