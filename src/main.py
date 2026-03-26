#!/usr/bin/env python3
"""
OMNIBOT v2.7 Titan - Multi-Market Trading Bot
Main entry point with all commands
"""

import sys
import os
import argparse
import hashlib
import getpass

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.settings import (
    VERSION, ALPACA, CRYPTO, FOREX, TRADING, 
    AUTO_UPDATER, EXTERNAL_ACCESS, DASHBOARD, TradingMode
)


def print_banner():
    """Print OMNIBOT banner"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 OMNIBOT v2.7.0 "Titan" - Multi-Market Trading Bot    ║
    ║                                                           ║
    ║   Markets: 📈 Stocks | 💰 Crypto | 💱 Forex              ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)


def change_password():
    """Change dashboard password"""
    print("🔐 Change Dashboard Password")
    print("-" * 40)
    
    current = getpass.getpass("Current password: ")
    
    # Verify current password
    if hashlib.sha256(current.encode()).hexdigest() != hashlib.sha256(DASHBOARD['password'].encode()).hexdigest():
        # Simple check for default
        if current != DASHBOARD['password']:
            print("❌ Incorrect current password")
            return
    
    new_pass = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm new password: ")
    
    if new_pass != confirm:
        print("❌ Passwords don't match")
        return
    
    if len(new_pass) < 4:
        print("❌ Password must be at least 4 characters")
        return
    
    # Update settings.py
    settings_path = os.path.join(PROJECT_ROOT, 'config', 'settings.py')
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # Replace password
    import re
    content = re.sub(
        r'"password":\s*"[^"]*"',
        f'"password": "{new_pass}"',
        content
    )
    
    with open(settings_path, 'w') as f:
        f.write(content)
    
    print("✅ Password changed successfully!")


def show_api_links():
    """Show all API signup links"""
    print("""
🔗 API Signup Links
═══════════════════════════════════════════════════════════

📈 STOCKS (Alpaca) - REQUIRED
   URL: https://alpaca.markets
   Steps:
   1. Sign up for free account
   2. Go to Paper Trading → View API Keys
   3. Copy API Key ID and Secret Key

💰 CRYPTO (Binance) - OPTIONAL
   URL: https://binance.com
   Testnet: https://testnet.binance.vision/
   Steps:
   1. Sign up and complete verification
   2. Go to API Management
   3. Create new API key with "Enable Reading" + "Spot Trading"

💱 FOREX (OANDA) - OPTIONAL
   URL: https://www.oanda.com/demo-account/
   Steps:
   1. Create free practice account
   2. Go to Manage Funds → API Access
   3. Generate personal access token

🌐 REMOTE ACCESS (Tailscale) - RECOMMENDED
   URL: https://login.tailscale.com/start
   Steps:
   1. Sign up with Google/Microsoft/GitHub
   2. Install on your devices
   3. Get permanent static IP for 24/7 access

═══════════════════════════════════════════════════════════
Run: python src/main.py --setup  to configure these APIs
""")


def show_trading_modes():
    """Show available trading modes"""
    print("""
🎮 Trading Modes
═══════════════════════════════════════════════════════════

🟢 CONSERVATIVE  - Low risk, 1% per trade, 300s scan interval
🔵 MODERATE      - Medium risk, 2% per trade, 120s scan interval  
🟠 AGGRESSIVE    - High risk, 5% per trade, 60s scan interval
🔴 HFT            - Very high risk, 0.5% per trade, 30s scan interval
🟣 SENTINEL       - AI adaptive risk management

Current mode: """ + TRADING['mode'].value.upper() + """
═══════════════════════════════════════════════════════════
""")


def show_tunnel_options():
    """Show remote access options"""
    print("""
🌐 Remote Access Options (No Port Forwarding Needed!)
═══════════════════════════════════════════════════════════

🥇 TAILSCALE (Recommended)
   ✓ Permanent static IP (100.x.x.x)
   ✓ Free for personal use
   ✓ Install: ./scripts/omnibot.sh install-tailscale
   ✓ Access: http://100.x.x.x:8081

🥈 CLOUDFLARE TUNNEL
   ✓ Custom domain support
   ✓ Free tier available
   ✓ Requires: cloudflared install

🥉 NGROK
   ✓ Random URL each restart
   ✓ Free tier: 1 concurrent tunnel
   ✓ Built-in: --ngrok flag

4️⃣ LOCALHOST.RUN
   ✓ No signup required
   ✓ SSH-based tunnel
   ✓ Command: ssh -R 80:localhost:8081 localhost.run

═══════════════════════════════════════════════════════════
""")


def run_setup_wizard():
    """Run interactive setup wizard"""
    try:
        from scripts.setup_wizard import main as wizard_main
        wizard_main()
    except ImportError:
        print("❌ Setup wizard not found")
        print("Running basic setup...")
        os.system(f"cd {PROJECT_ROOT} && bash setup.sh")


def check_api_status():
    """Check all API connections"""
    print("🔌 Checking API Status...")
    print("═" * 59)
    
    # Check Alpaca
    print("\n📈 ALPACA (Stocks):")
    if ALPACA.get('enabled'):
        try:
            import alpaca_trade_api as tradeapi
            api = tradeapi.REST(
                ALPACA['api_key'],
                ALPACA['secret_key'],
                ALPACA['base_url']
            )
            account = api.get_account()
            print(f"   ✅ Connected (Paper: {ALPACA.get('paper', True)})")
            print(f"   💰 Balance: ${float(account.portfolio_value):,.2f}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
    else:
        print("   ⚪ Disabled")
    
    # Check Crypto
    print("\n💰 CRYPTO (Binance):")
    if CRYPTO.get('enabled'):
        try:
            import ccxt
            exchange = getattr(ccxt, CRYPTO['exchange'])({
                'apiKey': CRYPTO['api_key'],
                'secret': CRYPTO['secret'],
                'enableRateLimit': True,
            })
            if CRYPTO.get('testnet'):
                exchange.set_sandbox_mode(True)
            balance = exchange.fetch_balance()
            print(f"   ✅ Connected (Testnet: {CRYPTO.get('testnet', True)})")
            print(f"   💰 Balance: ${balance.get('USDT', {}).get('free', 0):,.2f}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
    else:
        print("   ⚪ Disabled")
    
    # Check Forex
    print("\n💱 FOREX (OANDA):")
    if FOREX.get('enabled'):
        try:
            import v20
            ctx = v20.Context(
                hostname=FOREX['base_url'].replace('https://', ''),
                token=FOREX['access_token']
            )
            response = ctx.account.get(FOREX['account_id'])
            account = response.body['account']
            print(f"   ✅ Connected ({FOREX.get('environment', 'practice')})")
            print(f"   💰 Balance: ${float(account.NAV):,.2f}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
    else:
        print("   ⚪ Disabled")
    
    print("\n" + "═" * 59)


def run_dashboard(use_ngrok=False):
    """Run web dashboard"""
    try:
        from src.dashboard.app import create_app
        from src.core.multi_market_engine import get_multi_market_engine
        
        print("🌐 Starting Dashboard on 0.0.0.0:8081")
        
        engine = get_multi_market_engine()
        app = create_app(engine)
        
        if use_ngrok:
            try:
                from pyngrok import ngrok
                ngrok_tunnel = ngrok.connect(8081)
                print(f"🌍 Public URL: {ngrok_tunnel.public_url}")
                
                # Save URL to file
                with open(os.path.join(PROJECT_ROOT, '.ngrok_url'), 'w') as f:
                    f.write(ngrok_tunnel.public_url)
            except Exception as e:
                print(f"⚠️  Ngrok error: {e}")
        
        # Run with allow_unsafe_werkzeug for external access
        app.run(
            host='0.0.0.0',
            port=8081,
            debug=False,
            allow_unsafe_werkzeug=True
        )
        
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        import traceback
        traceback.print_exc()


def run_trading():
    """Run automated trading"""
    try:
        from src.core.multi_market_engine import get_multi_market_engine
        
        print("🤖 Starting Automated Trading...")
        engine = get_multi_market_engine()
        engine.run()
        
    except Exception as e:
        print(f"❌ Trading error: {e}")
        import traceback
        traceback.print_exc()


def install_tailscale():
    """Install Tailscale for 24/7 access"""
    print("📡 Installing Tailscale...")
    os.system("curl -fsSL https://tailscale.com/install.sh | sh")
    print("\n✅ Tailscale installed!")
    print("🔐 Starting authentication...")
    os.system("sudo tailscale up")
    print("\n📝 Your Tailscale IP:")
    os.system("tailscale ip -4")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='OMNIBOT v2.7 Titan')
    parser.add_argument('--version', action='store_true', help='Show version')
    parser.add_argument('--setup', action='store_true', help='Run setup wizard')
    parser.add_argument('--api-links', action='store_true', help='Show API signup links')
    parser.add_argument('--api-status', action='store_true', help='Check API status')
    parser.add_argument('--trading-modes', action='store_true', help='Show trading modes')
    parser.add_argument('--tunnel-options', action='store_true', help='Show remote access options')
    parser.add_argument('--change-password', action='store_true', help='Change dashboard password')
    parser.add_argument('--install-tailscale', action='store_true', help='Install Tailscale')
    parser.add_argument('--mode', choices=['dashboard', 'trading'], help='Run mode')
    parser.add_argument('--ngrok', action='store_true', help='Use ngrok tunnel')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"OMNIBOT {VERSION}")
        return
    
    print_banner()
    
    if args.setup:
        run_setup_wizard()
    elif args.api_links:
        show_api_links()
    elif args.api_status:
        check_api_status()
    elif args.trading_modes:
        show_trading_modes()
    elif args.tunnel_options:
        show_tunnel_options()
    elif args.change_password:
        change_password()
    elif args.install_tailscale:
        install_tailscale()
    elif args.mode == 'dashboard':
        run_dashboard(use_ngrok=args.ngrok)
    elif args.mode == 'trading':
        run_trading()
    else:
        parser.print_help()
        print("\n" + "═" * 59)
        print("🚀 Quick Start:")
        print("   python src/main.py --setup          # Configure APIs")
        print("   python src/main.py --mode dashboard # Start dashboard")
        print("   ./scripts/omnibot.sh start          # Start with auto-tunnel")
        print("═" * 59)


if __name__ == '__main__':
    main()