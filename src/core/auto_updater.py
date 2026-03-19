"""
OMNIBOT Auto-Updater - Weekend Updates
Fixed: Added Dict import for Python type hints
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any  # Fixed: Added Dict import

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import AUTO_UPDATER, BASE_DIR, VERSION

logger = logging.getLogger(__name__)


class AutoUpdater:
    """Handles automatic updates during market closures"""

    def __init__(self):
        self.enabled = AUTO_UPDATER.get('enabled', True)
        self.check_interval = AUTO_UPDATER.get('check_interval_hours', 24)
        self.auto_install = AUTO_UPDATER.get('auto_install', True)
        self.backup_before = AUTO_UPDATER.get('backup_before_update', True)
        self.weekend_only = AUTO_UPDATER.get('update_on_weekend', True)
        self.update_time = AUTO_UPDATER.get('update_time', '02:00')
        self.rollback_on_failure = AUTO_UPDATER.get('rollback_on_failure', True)
        self.version_url = AUTO_UPDATER.get('version_url', '')
        self.repo_url = AUTO_UPDATER.get('repo_url', '')

        self.last_check = None
        self.current_version = VERSION
        self.latest_version = None
        self.update_available = False

    def is_market_closed(self) -> bool:
        """Check if market is closed (weekend or after hours)"""
        now = datetime.now()

        # Weekend check
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return True

        # After hours check (assuming US market hours 9:30-16:00 ET)
        # This is a simplified check - adjust for your timezone
        hour = now.hour
        if hour < 9 or hour >= 16:
            return True

        return False

    def is_update_time(self) -> bool:
        """Check if it's the scheduled update time"""
        now = datetime.now()
        update_hour, update_minute = map(int, self.update_time.split(':'))

        if now.hour == update_hour and now.minute >= update_minute:
            return True
        return False

    def check_for_updates(self) -> bool:
        """Check if new version is available"""
        if not self.enabled:
            return False

        # Rate limit checks
        if self.last_check:
            time_since = datetime.now() - self.last_check
            if time_since < timedelta(hours=self.check_interval):
                return self.update_available

        try:
            # Check GitHub API for latest release
            import requests
            response = requests.get(self.version_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.latest_version = data.get('tag_name', 'v0.0.0').replace('v', '')

                # Compare versions
                if self._version_compare(self.latest_version, self.current_version) > 0:
                    self.update_available = True
                    logger.info(f"Update available: {self.current_version} -> {self.latest_version}")
                else:
                    self.update_available = False

            self.last_check = datetime.now()

        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return False

        return self.update_available

    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare two version strings"""
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]

        for i in range(max(len(parts1), len(parts2))):
            p1 = parts1[i] if i < len(parts1) else 0
            p2 = parts2[i] if i < len(parts2) else 0

            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1

        return 0

    def backup_current(self) -> bool:
        """Create backup before update"""
        if not self.backup_before:
            return True

        try:
            backup_dir = Path(BASE_DIR) / 'backups'
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f'backup_{timestamp}'

            # Create backup
            shutil.copytree(BASE_DIR, backup_path, ignore=shutil.ignore_patterns(
                'venv', '__pycache__', '*.pyc', '.git', 'backups'
            ))

            logger.info(f"Backup created: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    def perform_update(self) -> bool:
        """Perform the update"""
        if not self.update_available:
            return True

        if self.weekend_only and not self.is_market_closed():
            logger.info("Waiting for market close to update")
            return False

        if not self.is_update_time():
            return False

        logger.info(f"Starting update to version {self.latest_version}")

        # Create backup
        if not self.backup_current():
            logger.error("Update aborted - backup failed")
            return False

        try:
            # Download and install update
            updates_dir = Path(BASE_DIR) / 'updates'
            updates_dir.mkdir(exist_ok=True)

            # Clone latest version
            update_path = updates_dir / 'latest'
            if update_path.exists():
                shutil.rmtree(update_path)

            subprocess.run([
                'git', 'clone', '--depth', '1', 
                '--branch', f'v{self.latest_version}',
                self.repo_url, str(update_path)
            ], check=True, capture_output=True)

            # Apply update
            self._apply_update(update_path)

            logger.info("Update completed successfully")
            self.current_version = self.latest_version
            self.update_available = False
            return True

        except Exception as e:
            logger.error(f"Update failed: {e}")

            if self.rollback_on_failure:
                logger.info("Rolling back to previous version")
                self._rollback()

            return False

    def _apply_update(self, update_path: Path):
        """Apply the update files"""
        # Copy new files
        for item in update_path.iterdir():
            if item.name in ['venv', 'backups', 'updates', 'data']:
                continue

            dest = Path(BASE_DIR) / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    def _rollback(self):
        """Rollback to previous version"""
        # Find latest backup
        backup_dir = Path(BASE_DIR) / 'backups'
        if not backup_dir.exists():
            return

        backups = sorted(backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        if not backups:
            return

        latest_backup = backups[0]
        logger.info(f"Rolling back to: {latest_backup}")

        # Restore from backup
        for item in latest_backup.iterdir():
            dest = Path(BASE_DIR) / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    def run(self):
        """Main updater loop"""
        while True:
            if self.check_for_updates():
                self.perform_update()

            # Sleep until next check
            time.sleep(self.check_interval * 3600)


def start_auto_updater():
    """Start the auto-updater in background"""
    updater = AutoUpdater()

    # Run in separate thread
    import threading
    thread = threading.Thread(target=updater.run, daemon=True)
    thread.start()

    logger.info("Auto-updater started")
    return updater
