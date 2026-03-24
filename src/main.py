"""
OmniBot v2.6.1 Sentinel Enhanced
Main entry point with aggressive trading and auto-updates
"""

import sys
import os
import argparse
import signal
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import Settings, TradingMode
from core.auto_updater import AutoUpdater

def signal_handler(sig, frame):
    print("\n[MAIN] Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser(description='OmniBot v2.6.1 Sentinel Enhanced')
    parser.add_argument('--mode', choices=['conservative', 'moderate', 'aggressive', 'hft', 'sentinel'],
                       default='aggressive', help='Trading mode')
    parser.add_argument('--paper', action='store_true', help='Enable paper trading')
    parser.add_argument('--no-update', action='store_true', help='Disable auto-updates')
    parser.add_argument('--setup', action='store_true', help='Run initial setup')
    args = parser.parse_args()

    print("="*60)
    print("  🤖 OmniBot v2.6.1 Sentinel - Enhanced")
    print("  ML-Enhanced Automated Trading System")
    print("="*60)

    if args.setup:
        run_setup()
        return

    Settings.set_trading_mode(args.mode)
    Settings.PAPER_TRADING = args.paper

    if args.no_update:
        Settings.AUTO_UPDATE_ENABLED = False

    print(f"\n[CONFIG] Trading Mode: {args.mode.upper()}")
    print(f"[CONFIG] Paper Trading: {args.paper}")
    print(f"[CONFIG] Auto-Update: {Settings.AUTO_UPDATE_ENABLED}")
    print(f"[CONFIG] Weekend Updates: {Settings.UPDATE_ON_WEEKEND}")

    print("\n[INIT] Starting components...")

    updater = AutoUpdater(Settings)
    updater.start()

    print("\n[INIT] Starting dashboard on port 8081...")
    start_dashboard()

    print("\n" + "="*60)
    print("  ✅ OmniBot is running!")
    print("  📊 Dashboard: http://localhost:8081")
    print("="*60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

def start_dashboard():
    try:
        from dashboard.server import app
        import threading

        def run_dashboard():
            app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False)

        thread = threading.Thread(target=run_dashboard, daemon=True)
        thread.start()

    except Exception as e:
        print(f"[WARNING] Dashboard failed to start: {e}")

def run_setup():
    print("\n[SETUP] OmniBot v2.6 Setup Wizard")
    print("-" * 40)

    import sys
    print(f"Python version: {sys.version}")

    print("\n[SETUP] Installing dependencies...")
    deps = ['flask', 'flask-cors', 'numpy', 'pandas', 'requests', 'pyyaml']
    for dep in deps:
        print(f"  Installing {dep}...")
        os.system(f"pip install -q {dep}")

    print("\n[SETUP] Select default trading mode:")
    print("  1. Conservative (High confidence, low frequency)")
    print("  2. Moderate (Balanced)")
    print("  3. Aggressive (Lower thresholds, more trades)")
    print("  4. HFT Scalper (High frequency, short holds)")
    choice = input("  Choice (1-4, default=3): ").strip() or "3"

    modes = {'1': 'conservative', '2': 'moderate', '3': 'aggressive', '4': 'hft'}
    selected_mode = modes.get(choice, 'aggressive')

    with open('config/mode.txt', 'w') as f:
        f.write(selected_mode)

    print(f"\n[SETUP] Default mode set to: {selected_mode.upper()}")
    print("\n✅ Setup complete! Run with: python src/main.py")

if __name__ == '__main__':
    main()
