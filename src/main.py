#!/usr/bin/env python3
"""
OMNIBOT v2.6 Sentinel
Main entry point
"""

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import VERSION, VERSION_NAME, DASHBOARD
from src.core.trading_engine import TradingEngine
from src.backtest.engine import BacktestEngine
from src.dashboard.app import run_dashboard

# Setup logging
def setup_logging():
    """Configure logging"""
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"omnibot_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)

from datetime import datetime

logger = setup_logging()

def print_banner():
    """Print startup banner"""
    banner = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║           🤖 OMNIBOT v{VERSION} - {VERSION_NAME}                 ║
    ║                                                              ║
    ║     ML-Enhanced Trading System for Raspberry Pi              ║
    ║     Zero Cost • Fully Automated • Open Source                ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info(f"OMNIBOT v{VERSION} {VERSION_NAME} starting...")

async def run_trading():
    """Run trading mode"""
    print_banner()

    engine = TradingEngine()

    try:
        await engine.initialize()
        await engine.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        await engine.stop()

async def run_backtest(args):
    """Run backtest mode"""
    print_banner()

    logger.info(f"Starting backtest: {args.strategy} from {args.start} to {args.end}")

    from src.core.data_fetcher import DataFetcher
    import pandas as pd

    # Initialize components
    data_fetcher = DataFetcher()
    backtest_engine = BacktestEngine(
        initial_capital=args.capital,
        commission=args.commission,
        slippage=args.slippage
    )

    # Fetch data
    symbols = args.symbols.split(",")
    logger.info(f"Fetching data for: {symbols}")

    await data_fetcher.initialize()

    data = {}
    for symbol in symbols:
        df = await data_fetcher.get_stock_data(symbol, period="1y", interval="1d")
        if df is not None:
            data[symbol] = df

    if not data:
        logger.error("No data available for backtest")
        return

    # Run backtest
    start_date = pd.to_datetime(args.start)
    end_date = pd.to_datetime(args.end)

    result = backtest_engine.run_backtest(data, start_date, end_date)

    if result:
        # Print results
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Strategy: {result.strategy_name}")
        print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
        print(f"Initial Capital: ${result.initial_capital:,.2f}")
        print(f"Final Capital: ${result.final_capital:,.2f}")
        print(f"Total Return: {result.total_return_pct:.2f}%")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"Total Trades: {result.total_trades}")
        print(f"Win Rate: {result.win_rate:.1f}%")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print("="*60)

        # Save results
        if args.output:
            result.save(args.output)
            logger.info(f"Results saved to {args.output}")

    await data_fetcher.close()

def run_dashboard_server():
    """Run web dashboard"""
    print_banner()
    logger.info("Starting dashboard server...")
    run_dashboard()

def run_setup():
    """Interactive setup wizard"""
    print_banner()
    print("\n🔧 OMNIBOT Setup Wizard\n")

    print("This wizard will help you configure OMNIBOT v2.6\n")

    # Check if config exists
    config_path = Path("config/user_config.py")
    if config_path.exists():
        overwrite = input("Config already exists. Overwrite? (y/N): ").lower()
        if overwrite != "y":
            print("Setup cancelled.")
            return

    # Alpaca API keys
    print("\n📊 Alpaca API Configuration (Paper Trading)")
    print("Get your keys at: https://alpaca.markets/")
    alpaca_key = input("Alpaca API Key: ").strip()
    alpaca_secret = input("Alpaca Secret Key: ").strip()

    # Trading preferences
    print("\n⚙️  Trading Preferences")
    mode = input("Trading mode (paper/live) [paper]: ").strip() or "paper"
    capital = input("Initial capital [100000]: ").strip() or "100000"
    risk = input("Risk per trade (0.01-0.05) [0.02]: ").strip() or "0.02"

    # Create config
    config_content = f"""# User configuration - OMNIBOT v2.6
ALPACA_API_KEY = "{alpaca_key}"
ALPACA_SECRET_KEY = "{alpaca_secret}"
TRADING_MODE = "{mode}"
INITIAL_CAPITAL = {capital}
RISK_PER_TRADE = {risk}
"""

    with open(config_path, "w") as f:
        f.write(config_content)

    print(f"\n✅ Configuration saved to {config_path}")
    print("\nYou can now run OMNIBOT with: python src/main.py --mode trading")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description=f"OMNIBOT v{VERSION} {VERSION_NAME} - Automated Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py --mode trading          # Start trading
  python src/main.py --mode dashboard        # Start web dashboard
  python src/main.py --backtest --start 2023-01-01 --end 2024-01-01
  python src/main.py --setup                 # Run setup wizard
        """
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["trading", "dashboard", "cli"],
        default="cli",
        help="Operation mode"
    )

    parser.add_argument(
        "--backtest", "-b",
        action="store_true",
        help="Run backtest mode"
    )

    parser.add_argument(
        "--strategy", "-s",
        default="multi",
        help="Strategy to use (for backtest)"
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
        default="AAPL,MSFT,GOOGL",
        help="Comma-separated list of symbols"
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="Initial capital for backtest"
    )

    parser.add_argument(
        "--commission",
        type=float,
        default=0.001,
        help="Commission rate"
    )

    parser.add_argument(
        "--slippage",
        type=float,
        default=0.0005,
        help="Slippage rate"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file for backtest results"
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run setup wizard"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"OMNIBOT v{VERSION} {VERSION_NAME}"
    )

    args = parser.parse_args()

    if args.setup:
        run_setup()
    elif args.backtest:
        asyncio.run(run_backtest(args))
    elif args.mode == "trading":
        asyncio.run(run_trading())
    elif args.mode == "dashboard":
        run_dashboard_server()
    else:
        # CLI mode - interactive
        print_banner()
        print("\nAvailable commands:")
        print("  1. Start trading")
        print("  2. Start dashboard")
        print("  3. Run backtest")
        print("  4. Setup")
        print("  5. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            asyncio.run(run_trading())
        elif choice == "2":
            run_dashboard_server()
        elif choice == "3":
            args.backtest = True
            asyncio.run(run_backtest(args))
        elif choice == "4":
            run_setup()
        else:
            print("Goodbye!")

if __name__ == "__main__":
    main()
