#!/usr/bin/env python3
"""
OMNIBOT v2.6 Sentinel - Main Entry Point
"""

import sys
import os
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import VERSION, VERSION_NAME, DASHBOARD

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
    ║   🤖  OMNIBOT v{VERSION} {VERSION_NAME}                        ║
    ║                                                          ║
    ║   ML-Enhanced Automated Trading System                  ║
    ║   Raspberry Pi Optimized | Zero Cost | Open Source      ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="OMNIBOT v2.6 Sentinel")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--mode", choices=["trading", "dashboard"], help="Run mode")
    parser.add_argument("--ngrok", action="store_true", help="Enable ngrok")

    args = parser.parse_args()

    if args.version:
        print(f"OMNIBOT v{VERSION} {VERSION_NAME}")
        return

    print_banner()

    if args.setup:
        print("Setup wizard - edit config/settings.py manually for now")
        return

    if args.mode == "dashboard":
        from src.dashboard.app import run_dashboard
        print(f"Starting dashboard on port {DASHBOARD.get('port', 8081)}")
        run_dashboard(enable_ngrok=args.ngrok)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
