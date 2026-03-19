#!/usr/bin/env python3
"""
OMNIBOT v2.6 Sentinel - Main Entry Point
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import VERSION, VERSION_NAME, DASHBOARD, TRADING

# Configure logging
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
    """Print OMNIBOT banner"""
    banner = f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🤖  OMNIBOT v{VERSION} {VERSION_NAME}                        ║
    ║                                                          ║
    ║   ML-Enhanced Automated Trading System                  ║
    ║   Raspberry Pi Optimized | Zero Cost | Open Source      ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def setup_directories():
    """Create necessary directories"""
    dirs = [
        "data/cache",
        "data/logs", 
        "data/backtests",
        "backups",
        "updates"
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info("Directories initialized")


def run_setup_wizard():
    """Interactive setup wizard"""
    print("\n🔧 OMNIBOT Setup Wizard")
    print("=" * 50)

    # Check if config exists
    config_file = Path("config/user_config.py")
    if config_file.exists():
        overwrite = input("Config already exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return

    # API Keys
    print("\n📊 Alpaca API Configuration (get free at alpaca.markets)")
    api_key = input("Enter Alpaca API Key: ").strip()
    api_secret = input("Enter Alpaca Secret Key: ").strip()

    # Trading mode
    print("\n⚙️ Trading Mode")
    print("1. Paper Trading (recommended for testing)")
    print("2. Live Trading")
    mode_choice = input("Select (1/2): ").strip()
    mode = "live" if mode_choice == "2" else "paper"

    # Dashboard password
    print("\n🔐 Dashboard Security")
    password = input("Set dashboard password [admin]: ").strip() or "admin"

    # ngrok
    print("\n🌐 External Access (ngrok)")
    enable_ngrok = input("Enable ngrok on startup? (y/n): ").lower() == 'y'
    ngrok_token = ""
    if enable_ngrok:
        ngrok_token = input("Enter ngrok authtoken (from dashboard.ngrok.com): ").strip()

    # Generate config
    config_content = f""""\nUser configuration for OMNIBOT\n"""\n\n"
    config_content += f"# API Configuration\n"
    config_content += f"API = {{\n"
    config_content += f'    "alpaca_key": "{api_key}",\n'
    config_content += f'    "alpaca_secret": "{api_secret}",\n'
    config_content += f'    "alpaca_paper_url": "https://paper-api.alpaca.markets",\n'
    config_content += f'    "alpaca_live_url": "https://api.alpaca.markets"\n'
    config_content += f"}}\n\n"
    config_content += f"# Trading Settings\n"
    config_content += f'TRADING["mode"] = "{mode}"\n'
    config_content += f'TRADING["paper_capital"] = 100000.0\n\n'
    config_content += f"# Dashboard\n"
    config_content += f'DASHBOARD["password"] = "{password}"\n'
    config_content += f'DASHBOARD["allow_unsafe_werkzeug"] = True\n\n'
    config_content += f"# External Access\n"
    config_content += f'EXTERNAL_ACCESS["enabled"] = {enable_ngrok}\n'
    config_content += f'EXTERNAL_ACCESS["ngrok_authtoken"] = "{ngrok_token}"\n'
    config_content += f'EXTERNAL_ACCESS["keep_terminal_alive"] = True\n'

    # Write config
    with open(config_file, "w") as f:
        f.write(config_content)

    print(f"\n✅ Configuration saved to {config_file}")
    print("\n🚀 You can now start OMNIBOT:")
    print("   python src/main.py --mode trading")
    print("   python src/main.py --mode dashboard")


def run_trading_mode():
    """Run trading engine"""
    logger.info("Starting OMNIBOT Trading Engine...")

    try:
        from src.core.trading_engine import TradingEngine

        engine = TradingEngine()
        engine.start()

        print("\n🤖 Trading engine started. Press Ctrl+C to stop.\n")

        # Keep running
        while True:
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping trading engine...")
        engine.stop()
    except Exception as e:
        logger.error(f"Trading error: {e}")
        raise


def run_dashboard_mode(enable_ngrok=False):
    """Run web dashboard"""
    logger.info("Starting OMNIBOT Dashboard...")

    try:
        from src.dashboard.app import run_dashboard

        print("\n🌐 Starting dashboard server...")
        print(f"   Local: http://localhost:{DASHBOARD.get('port', 8080)}")

        if enable_ngrok:
            print("   Starting ngrok tunnel...")

        run_dashboard(enable_ngrok=enable_ngrok)

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise


def run_backtest(args):
    """Run backtesting"""
    logger.info("Starting OMNIBOT Backtest Engine...")

    try:
        from src.backtest.engine import BacktestEngine

        engine = BacktestEngine()

        symbols = args.symbols.split(",") if args.symbols else None

        results = engine.run(
            start_date=args.start,
            end_date=args.end,
            symbols=symbols
        )

        print("\n📊 Backtest Results:")
        print(f"   Period: {args.start} to {args.end}")
        print(f"   Total Return: {results.get('total_return', 0):.2f}%")
        print(f"   Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        print(f"   Max Drawdown: {results.get('max_drawdown', 0):.2f}%")
        print(f"   Win Rate: {results.get('win_rate', 0):.1f}%")

    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="OMNIBOT v2.6 Sentinel - Automated Trading System"
    )

    parser.add_argument(
        "--version", 
        action="store_true",
        help="Show version and exit"
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run setup wizard"
    )

    parser.add_argument(
        "--mode",
        choices=["trading", "dashboard"],
        help="Run mode: trading or dashboard"
    )

    parser.add_argument(
        "--ngrok",
        action="store_true",
        help="Enable ngrok tunnel for external access (dashboard mode)"
    )

    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest mode"
    )

    parser.add_argument(
        "--start",
        default="2023-01-01",
        help="Backtest start date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end",
        default="2024-01-01",
        help="Backtest end date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--symbols",
        help="Comma-separated list of symbols to backtest"
    )

    args = parser.parse_args()

    # Show version
    if args.version:
        print(f"OMNIBOT v{VERSION} {VERSION_NAME}")
        return

    print_banner()
    setup_directories()

    # Setup wizard
    if args.setup:
        run_setup_wizard()
        return

    # Trading mode
    if args.mode == "trading":
        run_trading_mode()
        return

    # Dashboard mode
    if args.mode == "dashboard":
        run_dashboard_mode(enable_ngrok=args.ngrok)
        return

    # Backtest mode
    if args.backtest:
        run_backtest(args)
        return

    # Default: show help
    parser.print_help()
    print("\n💡 Quick Start:")
    print("   python src/main.py --setup          # Configure OMNIBOT")
    print("   python src/main.py --mode trading   # Start trading")
    print("   python src/main.py --mode dashboard # Start dashboard")
    print("   python src/main.py --mode dashboard --ngrok  # With external access")


if __name__ == "__main__":
    main()
