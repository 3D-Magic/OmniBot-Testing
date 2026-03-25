#!/usr/bin/env python3
"""
OMNIBOT v2.7 Titan - Main Entry Point
Multi-Market Trading: Stocks + Crypto + Forex
24/7 Remote Access via Multiple Tunnel Options
"""

import sys
import os
import argparse
import logging
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    VERSION, VERSION_NAME, DASHBOARD, 
    ALPACA, CRYPTO, FOREX, TRADING_MODES, ACTIVE_MODE, REMOTE_ACCESS
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/omnibot.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    banner = f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🤖  OMNIBOT v{VERSION} {VERSION_NAME}                          ║
    ║                                                          ║
    ║   Multi-Market Trading System                           ║
    ║   Stocks • Crypto • Forex | 24/7 Automated              ║
    ║                                                          ║
    ║   Mode: {ACTIVE_MODE.upper():<20}                               ║
    ║   Tunnel: {REMOTE_ACCESS.get('primary_method', 'ngrok').upper():<15}                           ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_setup_wizard():
    """Run interactive setup wizard"""
    wizard_path = Path(__file__).parent.parent / "scripts" / "setup_wizard.py"
    if wizard_path.exists():
        import subprocess
        subprocess.run([sys.executable, str(wizard_path)])
    else:
        print("❌ Setup wizard not found")


def change_password():
    """Change dashboard password"""
    print("🔐 Change Dashboard Password")
    print("-" * 40)

    current = getpass.getpass("Current password: ")

    if current != DASHBOARD.get('password', 'admin'):
        print("❌ Incorrect current password!")
        return False

    new_pass = getpass.getpass("New password: ")
    confirm_pass = getpass.getpass("Confirm new password: ")

    if new_pass != confirm_pass:
        print("❌ Passwords don't match!")
        return False

    if len(new_pass) < 6:
        print("❌ Password must be at least 6 characters!")
        return False

    settings_path = Path(__file__).parent.parent / "config" / "settings.py"
    with open(settings_path, 'r') as f:
        content = f.read()

    old_line = f'"password": os.getenv("OMNIBOT_PASSWORD", "{DASHBOARD["password"]}")'
    new_line = f'"password": os.getenv("OMNIBOT_PASSWORD", "{new_pass}")'
    content = content.replace(old_line, new_line)

    with open(settings_path, 'w') as f:
        f.write(content)

    print("✅ Password changed successfully!")
    return True


def show_api_links():
    """Display API signup links"""
    print("""
    🔗 API SIGNUP LINKS - Get Your Free API Keys
    ═══════════════════════════════════════════════════════════

    📈 STOCKS (Alpaca - REQUIRED for stock trading)
       URL: https://alpaca.markets
       • Free paper trading with $100,000 virtual money
       • Commission-free live trading
       • Get API keys from dashboard after signup

    💰 CRYPTO (Binance/Coinbase/Kraken - Optional)
       • Binance: https://www.binance.com/en/my/settings/api-management
       • Coinbase: https://www.coinbase.com/settings/api
       • Kraken: https://www.kraken.com/u/security/api
       • Use TESTNET first (free practice money)

    💱 FOREX (OANDA - Optional)
       URL: https://www.oanda.com/demo-account/
       • Free practice account with $100,000 virtual
       • API docs: https://developer.oanda.com/

    🌐 REMOTE ACCESS OPTIONS
       • Tailscale: https://login.tailscale.com/start (Recommended)
       • Cloudflare: https://dash.cloudflare.com/sign-up
       • ngrok: https://dashboard.ngrok.com/signup

    ═══════════════════════════════════════════════════════════
    """)


def show_trading_modes():
    """Display available trading modes"""
    print("""
    📊 AVAILABLE TRADING MODES
    ═══════════════════════════════════════════════════════════
    """)

    for mode, config in TRADING_MODES.items():
        active = "✅ ACTIVE" if mode == ACTIVE_MODE else ""
        print(f"  {mode.upper():<15} - {config['description']}")
        print(f"                   Risk: {config['risk_per_trade']*100}% | Max Pos: {config['max_positions']} | Leverage: {config['leverage']}x {active}")
        print()

    print("  To change mode, edit config/settings.py and set ACTIVE_MODE")


def show_tunnel_options():
    """Display tunnel options"""
    from src.utils.tunnel_manager import show_tunnel_options
    show_tunnel_options()


def check_api_status():
    """Check if APIs are configured"""
    print("""
    🔍 API Configuration Status
    ═══════════════════════════════════════════════════════════
    """)

    # Check Alpaca
    if ALPACA.get('api_key') and ALPACA.get('secret_key'):
        print("  ✅ ALPACA (Stocks): Configured")
    else:
        print("  ❌ ALPACA (Stocks): NOT configured")
        print("     → Run: python src/main.py --setup")

    # Check Crypto
    if CRYPTO.get('enabled') and CRYPTO.get('api_key'):
        print("  ✅ CRYPTO: Enabled and configured")
    elif CRYPTO.get('enabled'):
        print("  ⚠️  CRYPTO: Enabled but NOT configured")
    else:
        print("  ⏸️  CRYPTO: Disabled")

    # Check Forex
    if FOREX.get('enabled') and FOREX.get('access_token'):
        print("  ✅ FOREX: Enabled and configured")
    elif FOREX.get('enabled'):
        print("  ⚠️  FOREX: Enabled but NOT configured")
    else:
        print("  ⏸️  FOREX: Disabled")

    print(f"
  📊 Active Trading Mode: {ACTIVE_MODE.upper()}")
    print(f"  🌐 Remote Access: {REMOTE_ACCESS.get('primary_method', 'ngrok').upper()}")
    print(f"  💡 Tip: Use --setup to configure all APIs")


def install_tailscale():
    """Install Tailscale"""
    from src.utils.tunnel_manager import install_tailscale
    install_tailscale()


def main():
    parser = argparse.ArgumentParser(
        description="OMNIBOT v2.7 Titan - Multi-Market Trading Bot"
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--setup", action="store_true", help="Run interactive setup wizard")
    parser.add_argument("--mode", choices=["trading", "dashboard"], help="Run mode")
    parser.add_argument("--tunnel", choices=["tailscale", "cloudflare", "ngrok", "localhost_run"], 
                       help="Tunnel method for remote access")
    parser.add_argument("--change-password", action="store_true", help="Change dashboard password")
    parser.add_argument("--api-links", action="store_true", help="Show API signup links")
    parser.add_argument("--api-status", action="store_true", help="Check API configuration")
    parser.add_argument("--trading-modes", action="store_true", help="Show available trading modes")
    parser.add_argument("--tunnel-options", action="store_true", help="Show tunnel options")
    parser.add_argument("--install-tailscale", action="store_true", help="Install Tailscale")

    args = parser.parse_args()

    if args.version:
        print(f"OMNIBOT v{VERSION} {VERSION_NAME}")
        print(f"Trading Mode: {ACTIVE_MODE}")
        print(f"Remote Access: {REMOTE_ACCESS.get('primary_method', 'ngrok')}")
        return

    if args.setup:
        run_setup_wizard()
        return

    if args.change_password:
        change_password()
        return

    if args.api_links:
        show_api_links()
        return

    if args.api_status:
        check_api_status()
        return

    if args.trading_modes:
        show_trading_modes()
        return

    if args.tunnel_options:
        show_tunnel_options()
        return

    if args.install_tailscale:
        install_tailscale()
        return

    print_banner()

    if args.mode == "dashboard":
        from src.dashboard.app import run_dashboard
        from src.utils.tunnel_manager import TunnelManager

        print(f"🚀 Starting dashboard on port {DASHBOARD.get('port', 8081)}")
        print(f"📊 Markets: Stocks {'✅' if ALPACA.get('api_key') else '❌'} | "
              f"Crypto {'✅' if CRYPTO.get('enabled') else '⏸️'} | "
              f"Forex {'✅' if FOREX.get('enabled') else '⏸️'}")
        print(f"⚙️  Trading Mode: {ACTIVE_MODE.upper()}")

        # Start tunnel if requested
        if args.tunnel:
            tunnel = TunnelManager()
            tunnel.start_tunnel(args.tunnel)

        run_dashboard()
        return

    if args.mode == "trading":
        print("🤖 Starting trading engine...")
        print(f"📈 Mode: {ACTIVE_MODE.upper()}")
        print("📊 Multi-market support: Stocks + Crypto + Forex")
        return

    parser.print_help()
    print("
💡 Quick start:")
    print("  python src/main.py --setup            # Interactive setup")
    print("  python src/main.py --api-links        # Get API signup URLs")
    print("  python src/main.py --tunnel-options   # View remote access options")
    print("  ./scripts/omnibot.sh start            # Start bot")


if __name__ == "__main__":
    main()
