"""
OMNIBOT v2.6 Sentinel - Weekend Auto-Updater
Automatically updates the bot during weekends when markets are closed
"""

import logging
import os
import shutil
import subprocess
import json
import zipfile
import requests
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

from config.settings import AUTO_UPDATE, VERSION

logger = logging.getLogger(__name__)

class AutoUpdater:
    """Handles automatic updates during weekends"""

    def __init__(self):
        self.config = AUTO_UPDATE
        self.update_window = self.config.get("update_window", {"day": "saturday", "time": "02:00"})
        self.check_interval = self.config.get("check_interval", 3600)
        self.running = False
        self.thread = None

    def start(self):
        """Start the auto-updater background thread"""
        if not self.config.get("enabled", False):
            logger.info("Auto-updater is disabled")
            return

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("Auto-updater started")

    def stop(self):
        """Stop the auto-updater"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Auto-updater stopped")

    def _update_loop(self):
        """Main update loop - checks every hour"""
        while self.running:
            try:
                if self._is_update_time() and self._is_market_closed():
                    logger.info("Update window reached and markets closed - checking for updates")
                    self._check_and_update()

                # Sleep for check interval
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Update loop error: {e}")
                time.sleep(self.check_interval)

    def _is_update_time(self) -> bool:
        """Check if current time is within update window"""
        now = datetime.now()

        # Check day
        target_day = self.update_window.get("day", "saturday").lower()
        current_day = now.strftime("%A").lower()

        if current_day != target_day:
            return False

        # Check time (within 1 hour window)
        target_time = self.update_window.get("time", "02:00")
        target_hour, target_minute = map(int, target_time.split(":"))

        current_time = now.time()
        target_datetime = datetime.combine(now.date(), 
                                         __import__("datetime").time(target_hour, target_minute))

        # Allow 1 hour window
        time_diff = abs((datetime.combine(now.date(), current_time) - target_datetime).total_seconds())

        return time_diff < 3600  # Within 1 hour

    def _is_market_closed(self) -> bool:
        """Check if stock market is closed (weekend or holiday)"""
        now = datetime.now()

        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return True

        # Check if outside market hours (9:30 AM - 4:00 PM ET)
        # This is a simplified check - for production, check actual market holidays
        et_time = now - timedelta(hours=5)  # Convert to ET (simplified)

        if et_time.weekday() < 5:  # Weekday
            market_open = et_time.replace(hour=9, minute=30, second=0)
            market_close = et_time.replace(hour=16, minute=0, second=0)

            if market_open <= et_time <= market_close:
                return False

        return True

    def _check_and_update(self):
        """Check for updates and apply if available"""
        try:
            # Check for new version
            latest_version = self._get_latest_version()

            if not latest_version:
                logger.info("Could not check for updates")
                return

            if self._version_compare(latest_version, VERSION) <= 0:
                logger.info(f"Current version {VERSION} is up to date")
                return

            logger.info(f"New version available: {latest_version}")

            # Backup current installation
            if self.config.get("backup_before_update", True):
                if not self._create_backup():
                    logger.error("Backup failed - aborting update")
                    return

            # Download update
            update_package = self._download_update(latest_version)
            if not update_package:
                logger.error("Download failed - aborting update")
                return

            # Apply update
            if self._apply_update(update_package):
                logger.info(f"Successfully updated to version {latest_version}")
                self._restart_bot()
            else:
                logger.error("Update failed")
                if self.config.get("rollback_on_failure", True):
                    self._rollback()

        except Exception as e:
            logger.error(f"Update error: {e}")
            if self.config.get("rollback_on_failure", True):
                self._rollback()

    def _get_latest_version(self) -> str:
        """Check GitHub for latest version"""
        try:
            # Check GitHub releases
            url = "https://api.github.com/repos/3D-Magic/OmniBot/releases/latest"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("tag_name", "").replace("v", "")

            # Fallback: check version file in repo
            url = "https://raw.githubusercontent.com/3D-Magic/OmniBot/main/version.txt"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.text.strip()

        except Exception as e:
            logger.error(f"Version check error: {e}")

        return None

    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns >0 if v1>v2, <0 if v1<v2, 0 if equal"""
        def parse_version(v):
            return [int(x) for x in v.split(".")]

        v1_parts = parse_version(v1)
        v2_parts = parse_version(v2)

        for i in range(max(len(v1_parts), len(v2_parts))):
            p1 = v1_parts[i] if i < len(v1_parts) else 0
            p2 = v2_parts[i] if i < len(v2_parts) else 0

            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1

        return 0

    def _create_backup(self) -> bool:
        """Create backup of current installation"""
        try:
            backup_dir = Path("backups") / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_dir.parent.mkdir(exist_ok=True)

            # Copy current src directory
            src_dir = Path("src")
            if src_dir.exists():
                shutil.copytree(src_dir, backup_dir / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

            # Copy config
            config_dir = Path("config")
            if config_dir.exists():
                shutil.copytree(config_dir, backup_dir / "config")

            # Copy version info
            with open(backup_dir / "version.txt", "w") as f:
                f.write(VERSION)

            logger.info(f"Backup created at {backup_dir}")
            return True

        except Exception as e:
            logger.error(f"Backup error: {e}")
            return False

    def _download_update(self, version: str) -> Path:
        """Download update package"""
        try:
            # Download from GitHub releases
            url = f"https://github.com/3D-Magic/OmniBot/releases/download/v{version}/omnibot-v{version}.zip"

            update_dir = Path("updates")
            update_dir.mkdir(exist_ok=True)

            package_path = update_dir / f"omnibot-v{version}.zip"

            response = requests.get(url, stream=True, timeout=30)

            if response.status_code == 200:
                with open(package_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Downloaded update to {package_path}")
                return package_path
            else:
                logger.error(f"Download failed: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Download error: {e}")

        return None

    def _apply_update(self, package_path: Path) -> bool:
        """Apply the downloaded update"""
        try:
            # Extract update
            extract_dir = Path("updates") / "extracted"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

            with zipfile.ZipFile(package_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Copy new files
            src_source = extract_dir / "src"
            if src_source.exists():
                src_target = Path("src")
                if src_target.exists():
                    shutil.rmtree(src_target)
                shutil.copytree(src_source, src_target)

            # Update version file
            with open("version.txt", "w") as f:
                f.write(self._get_latest_version())

            # Clean up
            shutil.rmtree(extract_dir)
            package_path.unlink()

            return True

        except Exception as e:
            logger.error(f"Update application error: {e}")
            return False

    def _rollback(self):
        """Rollback to previous version"""
        try:
            logger.info("Rolling back to previous version...")

            # Find latest backup
            backup_dir = Path("backups")
            if not backup_dir.exists():
                logger.error("No backups found for rollback")
                return

            backups = sorted(backup_dir.glob("backup_*"), reverse=True)
            if not backups:
                logger.error("No backups found for rollback")
                return

            latest_backup = backups[0]

            # Restore files
            src_backup = latest_backup / "src"
            if src_backup.exists():
                src_target = Path("src")
                if src_target.exists():
                    shutil.rmtree(src_target)
                shutil.copytree(src_backup, src_target)

            logger.info(f"Rolled back to {latest_backup}")

        except Exception as e:
            logger.error(f"Rollback error: {e}")

    def _restart_bot(self):
        """Restart the bot after update"""
        try:
            logger.info("Restarting OMNIBOT...")

            # Create restart flag
            with open(".restart", "w") as f:
                f.write(str(datetime.now()))

            # Exit current process - service manager will restart
            os._exit(0)

        except Exception as e:
            logger.error(f"Restart error: {e}")

    def check_now(self) -> Dict:
        """Manual check for updates (returns status)"""
        latest = self._get_latest_version()

        return {
            "current_version": VERSION,
            "latest_version": latest,
            "update_available": latest and self._version_compare(latest, VERSION) > 0,
            "can_update": self._is_market_closed()
        }

    def force_update(self) -> bool:
        """Force update now (manual trigger)"""
        if not self._is_market_closed():
            logger.warning("Markets are open - forcing update not recommended")

        try:
            self._check_and_update()
            return True
        except Exception as e:
            logger.error(f"Force update error: {e}")
            return False
