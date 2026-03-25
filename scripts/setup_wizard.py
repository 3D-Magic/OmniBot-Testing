#!/usr/bin/env python3
"""
OMNIBOT v2.7 Titan - Interactive Setup Wizard
Guides users through API setup and remote access configuration
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🤖  OMNIBOT v2.7 Titan - Setup Wizard                  ║
    ║                                                          ║
    ║   Multi-Market Trading | 24/7 Remote Access             ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)

def setup_alpaca():
    """Setup Alpaca API for stock trading"""
    print("\n📈 ALPACA - Stock Trading Setup")
    print("=" * 60)
    print("Alpaca provides FREE paper trading with $100,000 virtual money!")
    print("\n1. Visit: https://alpaca.markets")
    print("2. Click 'Get Started' and create an account")
    print("3. Go to Dashboard → Paper Trading")
    print("4. Generate API Keys (Paper Trading)")
    print("5. Copy the API Key ID and Secret Key\n")

    input("Press Enter when ready...")

    api_key = input("API Key ID: ").strip()
    secret_key = getpass.getpass("Secret Key: ").strip()

    if api_key and secret_key:
        # Update settings file
        settings_path = Path(__file__).parent.parent / "config" / "settings.py"
        with open(settings_path, 'r') as f:
            content = f.read()

        content = content.replace(
            '"api_key": os.getenv("ALPACA_API_KEY", "")',
            f'"api_key": "{api_key}"'
        )
        content = content.replace(
            '"secret_key": os.getenv("ALPACA_SECRET_KEY", "")',
            f'"secret_key": "{secret_key}"'
        )

        with open(settings_path, 'w') as f:
            f.write(content)

        print("✅ Alpaca API keys saved!")
        return True
    else:
        print("❌ Keys not provided. You can add them later in config/settings.py")
        return False

def setup_crypto():
    """Setup Crypto exchange API"""
    print("\n💰 CRYPTO Trading Setup (Optional)")
    print("=" * 60)
    print("Choose an exchange:")
    print("1. Binance (Recommended) - https://www.binance.com")
    print("2. Coinbase - https://www.coinbase.com")
    print("3. Kraken - https://www.kraken.com")
    print("4. Skip crypto setup")

    choice = input("\nSelect (1-4): ").strip()

    if choice == "4":
        print("⏭️  Skipping crypto setup")
        return False

    exchanges = {"1": "binance", "2": "coinbase", "3": "kraken"}
    exchange = exchanges.get(choice, "binance")

    print(f"\n📋 Steps for {exchange.upper()}:")
    if exchange == "binance":
        print("1. Login to https://www.binance.com")
        print("2. Go to Account → API Management")
        print("3. Create new API key (enable 'Enable Reading' and 'Enable Spot & Margin Trading')")
        print("4. IMPORTANT: Use TESTNET first!")
        print("   - Go to: https://testnet.binance.vision/")
        print("   - Create testnet API keys for practice")
    elif exchange == "coinbase":
        print("1. Login to https://www.coinbase.com")
        print("2. Go to Settings → API")
        print("3. Create new API key")
    elif exchange == "kraken":
        print("1. Login to https://www.kraken.com")
        print("2. Go to Settings → API")
        print("3. Create new API key")

    input("\nPress Enter when ready...")

    api_key = input("API Key: ").strip()
    secret = getpass.getpass("Secret: ").strip()

    if api_key and secret:
        settings_path = Path(__file__).parent.parent / "config" / "settings.py"
        with open(settings_path, 'r') as f:
            content = f.read()

        content = content.replace(
            '"exchange": "binance"',
            f'"exchange": "{exchange}"'
        )
        content = content.replace(
            '"enabled": False,  # Crypto',
            '"enabled": True,  # Crypto'
        )
        content = content.replace(
            '"api_key": os.getenv("CRYPTO_API_KEY", "")',
            f'"api_key": "{api_key}"'
        )
        content = content.replace(
            '"secret": os.getenv("CRYPTO_SECRET", "")',
            f'"secret": "{secret}"'
        )

        with open(settings_path, 'w') as f:
            f.write(content)

        print(f"✅ {exchange.upper()} API keys saved!")
        print("⚠️  Using TESTNET mode for safety. Set testnet=False for live trading.")
        return True

    return False

def setup_forex():
    """Setup OANDA API for forex trading"""
    print("\n💱 FOREX Trading Setup (Optional)")
    print("=" * 60)
    print("OANDA provides FREE practice accounts with $100,000 virtual money!")
    print("\n1. Visit: https://www.oanda.com/demo-account/")
    print("2. Create a demo account")
    print("3. Login to OANDA platform")
    print("4. Go to Manage Funds → API Access")
    print("5. Generate Personal Access Token\n")

    input("Press Enter when ready...")

    account_id = input("Account ID: ").strip()
    access_token = getpass.getpass("Access Token: ").strip()

    if account_id and access_token:
        settings_path = Path(__file__).parent.parent / "config" / "settings.py"
        with open(settings_path, 'r') as f:
            content = f.read()

        content = content.replace(
            '"enabled": False,  # Forex',
            '"enabled": True,  # Forex'
        )
        content = content.replace(
            '"account_id": os.getenv("OANDA_ACCOUNT_ID", "")',
            f'"account_id": "{account_id}"'
        )
        content = content.replace(
            '"access_token": os.getenv("OANDA_ACCESS_TOKEN", "")',
            f'"access_token": "{access_token}"'
        )

        with open(settings_path, 'w') as f:
            f.write(content)

        print("✅ OANDA API keys saved!")
        print("⚠️  Using PRACTICE environment. Change to 'live' for real trading.")
        return True

    print("⏭️  Skipping forex setup")
    return False

def setup_remote_access():
    """Setup remote access options"""
    print("\n🌐 REMOTE ACCESS Setup (No Port Forwarding Needed)")
    print("=" * 60)
    print("Choose your preferred method for 24/7 remote access:")
    print()
    print("1. 🥇 TAILSCALE (Recommended)")
    print("   • FREE for personal use")
    print("   • Static IP address (never changes)")
    print("   • Full network access (SSH, dashboard, files)")
    print("   • Works even if IP changes")
    print("   • Sign up: https://login.tailscale.com/start")
    print()
    print("2. 🥈 CLOUDFLARE TUNNEL")
    print("   • FREE with custom domain support")
    print("   • Most professional option")
    print("   • Requires domain name")
    print("   • Sign up: https://dash.cloudflare.com/sign-up")
    print()
    print("3. 🥉 NGROK (Built-in)")
    print("   • FREE tier available")
    print("   • Random URL (changes on restart)")
    print("   • Easiest setup")
    print("   • Sign up: https://dashboard.ngrok.com/signup")
    print()
    print("4. LOCALHOST.RUN (Free, no signup)")
    print("   • Completely free")
    print("   • No account needed")
    print("   • SSH-based tunnel")
    print()
    print("5. Skip for now")

    choice = input("\nSelect (1-5): ").strip()

    if choice == "1":
        print("\n📋 Tailscale Setup Instructions:")
        print("1. Sign up at https://login.tailscale.com/start")
        print("2. Install on this server:")
        print("   curl -fsSL https://tailscale.com/install.sh | sudo bash")
        print("   sudo tailscale up")
        print("3. Install Tailscale on your phone/laptop")
        print("4. Access OMNIBOT at: http://your-server-name:8081")
        print("\n✅ Tailscale will be installed automatically when you run setup.sh")

        # Update settings
        settings_path = Path(__file__).parent.parent / "config" / "settings.py"
        with open(settings_path, 'r') as f:
            content = f.read()
        content = content.replace(
            '"primary_method": "ngrok"',
            '"primary_method": "tailscale"'
        )
        with open(settings_path, 'w') as f:
            f.write(content)

    elif choice == "2":
        print("\n📋 Cloudflare Tunnel Setup:")
        print("1. Sign up at https://dash.cloudflare.com/sign-up")
        print("2. Add your domain to Cloudflare")
        print("3. Install cloudflared:")
        print("   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb")
        print("   sudo dpkg -i cloudflared-linux-amd64.deb")
        print("4. Authenticate: cloudflared tunnel login")
        print("5. Create tunnel: cloudflared tunnel create omnibot")

    elif choice == "3":
        print("\n📋 Ngrok Setup:")
        print("1. Sign up at https://dashboard.ngrok.com/signup")
        print("2. Get your authtoken from dashboard")
        print("3. Install: sudo apt install ngrok")
        print("4. Configure: ngrok config add-authtoken YOUR_TOKEN")
        print("5. OMNIBOT will start ngrok automatically with --ngrok flag")

        token = input("\nEnter ngrok authtoken (optional): ").strip()
        if token:
            # Save to environment
            bashrc = Path.home() / ".bashrc"
            with open(bashrc, 'a') as f:
                f.write(f'\nexport NGROK_TOKEN="{token}"\n')
            print("✅ Token saved to ~/.bashrc")

    elif choice == "4":
        print("\n📋 localhost.run Setup:")
        print("This requires no setup! Just run:")
        print("   ssh -R 80:localhost:8081 localhost.run")
        print("Or use the built-in OMNIBOT command:")
        print("   python src/main.py --tunnel localhost_run")

    input("\nPress Enter to continue...")

def select_trading_mode():
    """Select trading mode"""
    print("\n📊 SELECT TRADING MODE")
    print("=" * 60)
    print("Choose your risk level:")
    print()
    print("1. CONSERVATIVE (1% risk, 5 max positions)")
    print("   • Best for beginners")
    print("   • Low risk, steady growth")
    print()
    print("2. MODERATE (2% risk, 10 max positions) ⭐ RECOMMENDED")
    print("   • Balanced risk/reward")
    print("   • Good for most traders")
    print()
    print("3. AGGRESSIVE (5% risk, 15 max positions)")
    print("   • High risk, high reward")
    print("   • For experienced traders")
    print()
    print("4. HFT SCALPER (2% risk, 20 positions, 3x leverage)")
    print("   • High frequency trading")
    print("   • Many small trades")
    print()
    print("5. SENTINEL (2.5% risk, AI-enhanced)")
    print("   • AI can override signals")
    print("   • Smart adaptive trading")

    choice = input("\nSelect (1-5) [2]: ").strip() or "2"

    modes = {
        "1": "conservative",
        "2": "moderate",
        "3": "aggressive",
        "4": "hft_scalper",
        "5": "sentinel"
    }

    selected = modes.get(choice, "moderate")

    settings_path = Path(__file__).parent.parent / "config" / "settings.py"
    with open(settings_path, 'r') as f:
        content = f.read()

    content = content.replace(
        'ACTIVE_MODE = "moderate"',
        f'ACTIVE_MODE = "{selected}"'
    )

    with open(settings_path, 'w') as f:
        f.write(content)

    print(f"✅ Trading mode set to: {selected.upper()}")

def main():
    print_banner()

    print("\nThis wizard will help you set up OMNIBOT v2.7 Titan")
    print("You can configure:")
    print("  • Stock trading (Alpaca)")
    print("  • Crypto trading (Binance/Coinbase/Kraken)")
    print("  • Forex trading (OANDA)")
    print("  • Remote access (Tailscale/Cloudflare/ngrok)")
    print("  • Trading mode (Conservative/Moderate/Aggressive)")

    input("\nPress Enter to start...")

    # Setup markets
    setup_alpaca()

    enable_crypto = input("\nEnable crypto trading? (y/n): ").lower().strip()
    if enable_crypto == 'y':
        setup_crypto()

    enable_forex = input("\nEnable forex trading? (y/n): ").lower().strip()
    if enable_forex == 'y':
        setup_forex()

    # Trading mode
    select_trading_mode()

    # Remote access
    setup_remote_access()

    # Summary
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review your settings: nano config/settings.py")
    print("  2. Change password: python src/main.py --change-password")
    print("  3. Start OMNIBOT: ./scripts/omnibot.sh start")
    print("  4. Access dashboard: http://localhost:8081")
    print("\nFor help: python src/main.py --help")

if __name__ == "__main__":
    main()
