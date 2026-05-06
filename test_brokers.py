#!/usr/bin/env python3
import json, os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')

def load_settings():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def test_alpaca(cfg):
    print("\n--- Alpaca Test ---")
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(cfg['api_key'], cfg['secret_key'], paper=cfg.get('paper', True))
        account = client.get_account()
        print(f"✅ Connected")
        print(f"   Account:         {account.account_number}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):.2f}")
        print(f"   Buying Power:    ${float(account.buying_power):.2f}")
    except Exception as e:
        print(f"❌ Failed: {e}")

def test_binance(cfg):
    print("\n--- Binance Test ---")
    try:
        from binance.client import Client
        client = Client(cfg['api_key'], cfg['secret_key'], testnet=cfg.get('testnet', True))
        account = client.get_account()
        print(f"✅ Connected")
        balances = {b['asset']: float(b['free'])+float(b['locked']) for b in account['balances'] if float(b['free'])+float(b['locked']) > 0}
        print(f"   Balances: {balances}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == '__main__':
    settings = load_settings()
    brokers = settings.get('brokers', {})
    if brokers.get('alpaca', {}).get('api_key'):
        test_alpaca(brokers['alpaca'])
    else:
        print("Alpaca API key not set")
    if brokers.get('binance', {}).get('api_key'):
        test_binance(brokers['binance'])
    else:
        print("Binance API key not set")
