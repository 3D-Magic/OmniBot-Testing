"""
OMNIBOT v2.7 Titan - Auto-Updater
Automated weekend updates with rollback support
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import threading
from datetime import datetime, timedelta

from typing import Dict

logger = logging.getLogger(__name__)


class AutoUpdater:
    """
    Automated update system
    - Checks GitHub for new releases
    - Only updates on weekends (when markets closed)
    - Creates backups before updating
    - Auto-rollback on failure
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.check_interval = config.get('check_interval_hours', 24) * 3600
        self.auto_install = config.get('auto_install', True)
        self.update_on_weekend = config.get('update_on_weekend', True)
        self.update_time = config.get('update_time', '02:00')
        self.rollback_on_failure = config.get('rollback_on_failure', True)
        self.version_url = config.get('version_url', '')
        self.repo_url = config.get('repo_url', '')
        
        self.running = False
        self.last_check = None
        self.current_version = None
    
    def start(self):
        """Start auto-updater in background thread"""
        if not self.enabled:
            logger.info("Auto-updater disabled")
            return
        
        self.running = True
        thread = threading.Thread(target=self._update_loop, daemon=True)
        thread.start()
        logger.info("✅ Auto-updater started")
    
    def stop(self):
        """Stop auto-updater"""
        self.running = False
    
    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                if self._should_check_update():
                    self.check_for_updates()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Auto-updater error: {e}")
                time.sleep(3600)  # Sleep 1 hour on error
    
    def _should_check_update(self) -> bool:
        """Check if it's time to check for updates"""
        if self.last_check is None:
            return True
        
        elapsed = time.time() - self.last_check
        return elapsed >= self.check_interval
    
    def _is_weekend(self) -> bool:
        """Check if today is weekend"""
        today = datetime.now().weekday()
        return today >= 5  # 5 = Saturday, 6 = Sunday
    
    def _is_update_time(self) -> bool:
        """Check if it's the scheduled update time"""
        now = datetime.now()
        hour, minute = map(int, self.update_time.split(':'))
        return now.hour == hour and now.minute == minute
    
    def check_for_updates(self):
        """Check GitHub for new releases"""
        logger.info("Checking for updates...")
        self.last_check = time.time()
        
        try:
            import requests
            response = requests.get(self.version_url, timeout=30)
            
            if response.status_code == 200:
                latest = response.json()
                latest_version = latest.get('tag_name', 'v0.0.0')
                
                if self._is_newer_version(latest_version):
                    logger.info(f"New version available: {latest_version}")
                    
                    if self.auto_install and self._can_update_now():
                        self.perform_update(latest)
                else:
                    logger.debug("No updates available")
                    
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
    
    def _is_newer_version(self, version: str) -> bool:
        """Compare version strings"""
        # Simple version comparison
        current = self._parse_version(self.current_version or 'v2.7.0')
        latest = self._parse_version(version)
        return latest > current
    
    def _parse_version(self, version: str) -> tuple:
        """Parse version string to tuple"""
        version = version.lstrip('v')
        parts = version.split('.')
        return tuple(int(p) for p in parts[:3])
    
    def _can_update_now(self) -> bool:
        """Check if we can update now (weekend check)"""
        if not self.update_on_weekend:
            return True
        
        return self._is_weekend() and self._is_update_time()
    
    def perform_update(self, release_info: Dict):
        """Perform the update"""
        logger.info("Starting update...")
        
        # Create backup
        if not self._create_backup():
            logger.error("Backup failed, aborting update")
            return
        
        try:
            # Download and install
            self._download_update(release_info)
            self._install_update()
            
            logger.info("✅ Update completed successfully")
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            
            if self.rollback_on_failure:
                logger.info("Rolling back to previous version...")
                self._rollback()
    
    def _create_backup(self) -> bool:
        """Create backup of current installation"""
        try:
            backup_dir = os.path.join('backups', datetime.now().strftime('%Y%m%d_%H%M%S'))
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup key directories
            for item in ['src', 'config', 'scripts']:
                src = item
                dst = os.path.join(backup_dir, item)
                if os.path.exists(src):
                    shutil.copytree(src, dst)
            
            logger.info(f"✅ Backup created: {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def _download_update(self, release_info: Dict):
        """Download update from GitHub"""
        import requests
        
        # Get download URL
        assets = release_info.get('assets', [])
        if not assets:
            raise Exception("No assets found in release")
        
        download_url = assets[0].get('browser_download_url')
        
        # Download
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # Save to updates directory
        update_path = os.path.join('updates', 'latest.zip')
        os.makedirs('updates', exist_ok=True)
        
        with open(update_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info("✅ Update downloaded")
    
    def _install_update(self):
        """Install the downloaded update"""
        update_path = os.path.join('updates', 'latest.zip')
        
        if not os.path.exists(update_path):
            raise Exception("Update file not found")
        
        # Extract update
        import zipfile
        with zipfile.ZipFile(update_path, 'r') as zip_ref:
            zip_ref.extractall('updates/extracted')
        
        # Run install script
        install_script = os.path.join('updates/extracted', 'install.sh')
        if os.path.exists(install_script):
            subprocess.run(['bash', install_script], check=True)
        
        logger.info("✅ Update installed")
    
    def _rollback(self):
        """Rollback to previous version"""
        try:
            # Find latest backup
            backups = sorted(os.listdir('backups'))
            if not backups:
                logger.error("No backups found for rollback")
                return
            
            latest_backup = os.path.join('backups', backups[-1])
            
            # Restore from backup
            for item in ['src', 'config', 'scripts']:
                src = os.path.join(latest_backup, item)
                dst = item
                
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                if os.path.exists(src):
                    shutil.copytree(src, dst)
            
            logger.info("✅ Rollback completed")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")