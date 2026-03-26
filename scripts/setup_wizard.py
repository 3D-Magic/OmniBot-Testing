#!/usr/bin/env python3
"""
OMNIBOT v2.7 Titan - Interactive Setup Wizard
Guides users through API configuration
"""

import os
import sys
import getpass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.settings import VERSION


def print_banner():
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 OMNIBOT {VERSION} Setup Wizard                        ║
    ║                                                           ║
    ║   Let's configure your trading bot!                       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)


def get_input(prompt, default=None, password=False):
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    if password:
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    
    return value.strip() if value.strip() else default


def setup_alpaca():
    """Setup Alpaca API for stocks"""
    print("\n📈 ALPACA (Stocks) Setup")
    print("-" * 50)
    print("Get your API keys at: https://alpaca.markets")
    print("1. Sign up → 2. Paper Trading → 3. View API Keys")
    print("-" * 50)
    
    enabled = get_input("Enable stock trading? (yes/no)", "yes").lower() == "yes"
    
    if not enabled:
        return None
    
    api_key = get_input("API Key ID")
    secret_key = get_input("Secret Key", password=True)
    paper = get_input("Use paper trading? (yes/no)", "yes").lower() == "yes"
    
    return {
        "enabled": True,
        "api_key": api_key,
        "secret_key": secret_key,
        "paper": paper,
        "base_url": "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
    }


def setup_crypto():
    """Setup Crypto exchange"""
    print("\n💰 CRYPTO Setup")
    print("-" * 50)
    print("Supported: binance, coinbase, kraken, kucoin")
    print("Get keys at your exchange's API management page")
    print("-" * 50)
    
    enabled = get_input("Enable crypto trading? (yes/no)", "no").lower() == "yes"
    
    if not enabled:
        return None
    
    exchange = get_input("Exchange (binance/coinbase/kraken)", "binance")
    api_key = get_input("API Key")
    secret = get_input("API Secret", password=True)
    testnet = get_input("Use testnet first? (yes/no)", "yes").lower() == "yes"
    
    return {
        "enabled": True,
        "exchange": exchange,
        "api_key": api_key,
        "secret": secret,
        "testnet": testnet,
        "sandbox": testnet,
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD"]
    }


def setup_forex():
    """Setup OANDA for forex"""
    print("\n💱 FOREX (OANDA) Setup")
    print("-" * 50)
    print("Get your token at: https://www.oanda.com/demo-account/")
    print("Manage Funds → API Access → Generate Token")
    print("-" * 50)
    
    enabled = get_input("Enable forex trading? (yes/no)", "no").lower() == "yes"
    
    if not enabled:
        return None
    
    account_id = get_input("Account ID")
    access_token = get_input("Access Token", password=True)
    environment = get_input("Environment (practice/live)", "practice")
    
    return {
        "enabled": True,
        "account_id": account_id,
        "access_token": access_token,
        "environment": environment,
        "base_url": "https://api-fxpractice.oanda.com" if environment == "practice" else "https://api-fxtrade.oanda.com",
        "symbols": ["EUR_USD", "GBP_USD", "USD_JPY"]
    }


def setup_trading_mode():
    """Setup trading mode"""
    print("\n🎮 TRADING MODE Setup")
    print("-" * 50)
    print("conservative - Low risk, 1% per trade")
    print("moderate     - Medium risk, 2% per trade (recommended)")
    print("aggressive   - High risk, 5% per trade")
    print("hft          - Very high frequency, 0.5% per trade")
    print("sentinel     - AI adaptive risk management")
    print("-" * 50)
    
    mode = get_input("Trading mode", "moderate")
    return mode


def save_config(config):
    """Save configuration to settings.py"""
    settings_path = os.path.join(PROJECT_ROOT, "config", "settings.py")
    
    # Read current settings
    with open(settings_path, "r") as f:
        content = f.read()
    
    # Update ALPACA
    if "alpaca" in config:
        alpaca = config["alpaca"]
        content = content.replace(
            '"enabled": True,  # Set to False to disable',
            f'"enabled": {alpaca["enabled"]},'
        )
        content = content.replace(
            '"api_key": os.getenv("ALPACA_API_KEY", "YOUR_ALPACA_API_KEY_HERE")',
            f'"api_key": "{alpaca["api_key"]}",'
        )
        content = content.replace(
            '"secret_key": os.getenv("ALPACA_SECRET_KEY", "YOUR_ALPACA_SECRET_KEY_HERE")',
            f'"secret_key": "{alpaca["secret_key"]}",'
        )
        content = content.replace(
            '"paper": True,',
            f'"paper": {alpaca["paper"]},'
        )
    
    # Update CRYPTO
    if "crypto" in config:
        crypto = config["crypto"]
        content = content.replace(
            '"enabled": False,  # Set to True to enable crypto trading',
            f'"enabled": {crypto["enabled"]},'
        )
        content = content.replace(
            '"exchange": "binance",  # binance, coinbase, kraken, kucoin, etc.',
            f'"exchange": "{crypto["exchange"]}",'
        )
        content = content.replace(
            '"api_key": os.getenv("CRYPTO_API_KEY", "YOUR_CRYPTO_API_KEY_HERE")',
            f'"api_key": "{crypto["api_key"]}",'
        )
        content = content.replace(
            '"secret": os.getenv("CRYPTO_SECRET", "YOUR_CRYPTO_SECRET_HERE")',
            f'"secret": "{crypto["secret"]}",'
        )
        content = content.replace(
            '"testnet": True,',
            f'"testnet": {crypto["testnet"]},'
        )
    
    # Update FOREX
    if "forex" in config:
        forex = config["forex"]
        content = content.replace(
            '"enabled": False,  # Set to True to enable forex trading',
            f'"enabled": {forex["enabled"]},'
        )
        content = content.replace(
            '"account_id": os.getenv("OANDA_ACCOUNT_ID", "YOUR_OANDA_ACCOUNT_ID")',
            f'"account_id": "{forex["account_id"]}",'
        )
        content = content.replace(
            '"access_token": os.getenv("OANDA_ACCESS_TOKEN", "YOUR_OANDA_ACCESS_TOKEN")',
            f'"access_token": "{forex["access_token"]}",'
        )
        content = content.replace(
            '"environment": "practice",',
            f'"environment": "{forex["environment"]}",'
        )
    
    # Write updated settings
    with open(settings_path, "w") as f:
        f.write(content)
    
    print(f"\n✅ Configuration saved to {settings_path}")


def main():
    """Main wizard flow"""
    print_banner()
    
    print("Welcome! This wizard will help you configure OMNIBOT.")
    print("You'll need API keys from the trading platforms you want to use.")
    print("\nPress Ctrl+C at any time to cancel.")
    
    config = {}
    
    try:
        # Setup each market
        config["alpaca"] = setup_alpaca()
        config["crypto"] = setup_crypto()
        config["forex"] = setup_forex()
        config["trading_mode"] = setup_trading_mode()
        
        # Confirm
        print("\n" + "=" * 50)
        print("CONFIGURATION SUMMARY")
        print("=" * 50)
        print(f"Stocks: {'✅ Enabled' if config['alpaca'] else '❌ Disabled'}")
        print(f"Crypto: {'✅ Enabled' if config['crypto'] else '❌ Disabled'}")
        print(f"Forex:  {'✅ Enabled' if config['forex'] else '❌ Disabled'}")
        print(f"Mode:   {config['trading_mode']}")
        
        confirm = get_input("\nSave this configuration? (yes/no)", "yes")
        
        if confirm.lower() == "yes":
            save_config(config)
            print("\n🎉 Setup complete!")
            print("\nNext steps:")
            print("1. Review config/settings.py")
            print("2. Start with: ./scripts/omnibot.sh start")
        else:
            print("\n❌ Setup cancelled. No changes made.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()