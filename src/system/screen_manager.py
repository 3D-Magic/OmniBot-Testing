"""
Screen Manager for Raspberry Pi
Handles screen brightness, sleep/wake, and display control
"""
import subprocess
import os
import time
import threading
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ScreenManager:
    """Manage Raspberry Pi screen brightness and sleep/wake"""
    
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.sleep_timer = None
        self.is_sleeping = False
        self.last_activity = time.time()
        
        # Default settings
        self.brightness = self.settings.get('screen_brightness', 100)
        self.sleep_after_seconds = self.settings.get('screen_sleep_seconds', 300)  # 5 minutes default
        self.sleep_enabled = self.settings.get('screen_sleep_enabled', True)
        
        # Display paths
        self.backlight_path = self._find_backlight_path()
        self.x_display = os.environ.get('DISPLAY', ':0')
        
        # Start sleep monitor thread
        if self.sleep_enabled:
            self._start_sleep_monitor()
        
        logger.info(f"[SCREEN] Manager initialized - brightness: {self.brightness}%, sleep: {self.sleep_after_seconds}s")
    
    def _find_backlight_path(self) -> Optional[str]:
        """Find the backlight control path"""
        possible_paths = [
            '/sys/class/backlight/rpi_backlight',
            '/sys/class/backlight/10-0045',
            '/sys/class/backlight/pwm-backlight',
            '/sys/class/backlight/aml-bl',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                brightness_file = os.path.join(path, 'brightness')
                if os.path.exists(brightness_file):
                    logger.info(f"[SCREEN] Found backlight at {path}")
                    return path
        
        logger.warning("[SCREEN] No backlight control found")
        return None
    
    def _start_sleep_monitor(self):
        """Start the sleep monitor thread"""
        def monitor():
            while True:
                time.sleep(1)
                
                if not self.sleep_enabled:
                    continue
                
                if self.is_sleeping:
                    continue
                
                inactive_time = time.time() - self.last_activity
                if inactive_time >= self.sleep_after_seconds:
                    self.sleep()
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
        logger.info("[SCREEN] Sleep monitor started")
    
    def activity(self):
        """Record user activity (prevents sleep)"""
        self.last_activity = time.time()
        
        if self.is_sleeping:
            self.wake()
    
    def get_brightness(self) -> int:
        """Get current brightness (0-100)"""
        try:
            if self.backlight_path:
                brightness_file = os.path.join(self.backlight_path, 'brightness')
                max_brightness_file = os.path.join(self.backlight_path, 'max_brightness')
                
                with open(brightness_file, 'r') as f:
                    current = int(f.read().strip())
                
                with open(max_brightness_file, 'r') as f:
                    max_val = int(f.read().strip())
                
                return int((current / max_val) * 100)
            
            # Fallback: try xrandr
            result = subprocess.run(
                ['xrandr', '--verbose', '--display', self.x_display],
                capture_output=True, text=True, timeout=5
            )
            
            # Parse brightness from output
            for line in result.stdout.split('\n'):
                if 'Brightness:' in line:
                    try:
                        val = float(line.split(':')[1].strip())
                        return int(val * 100)
                    except:
                        pass
            
            return self.brightness
            
        except Exception as e:
            logger.error(f"[SCREEN] Error getting brightness: {e}")
            return self.brightness
    
    def set_brightness(self, percent: int) -> Dict:
        """Set screen brightness (0-100)"""
        try:
            percent = max(0, min(100, percent))
            self.brightness = percent
            
            if self.backlight_path:
                max_brightness_file = os.path.join(self.backlight_path, 'max_brightness')
                brightness_file = os.path.join(self.backlight_path, 'brightness')
                
                with open(max_brightness_file, 'r') as f:
                    max_val = int(f.read().strip())
                
                new_value = int((percent / 100) * max_val)
                
                with open(brightness_file, 'w') as f:
                    f.write(str(new_value))
                
                logger.info(f"[SCREEN] Brightness set to {percent}%")
                return {'success': True, 'brightness': percent}
            
            # Fallback: try xrandr
            result = subprocess.run(
                ['xrandr', '--display', self.x_display, '--output', 'HDMI-1', '--brightness', str(percent / 100)],
                capture_output=True, timeout=5
            )
            
            if result.returncode == 0:
                logger.info(f"[SCREEN] Brightness set to {percent}% via xrandr")
                return {'success': True, 'brightness': percent}
            
            return {'success': False, 'error': 'Could not set brightness'}
            
        except Exception as e:
            logger.error(f"[SCREEN] Error setting brightness: {e}")
            return {'success': False, 'error': str(e)}
    
    def sleep(self) -> Dict:
        """Put screen to sleep (blank)"""
        try:
            if self.is_sleeping:
                return {'success': True, 'message': 'Already sleeping'}
            
            # Save current brightness
            self._pre_sleep_brightness = self.get_brightness()
            
            # Turn off display
            if self.backlight_path:
                brightness_file = os.path.join(self.backlight_path, 'brightness')
                with open(brightness_file, 'w') as f:
                    f.write('0')
            
            # Also use xset to blank screen
            subprocess.run(
                ['xset', '-display', self.x_display, 'dpms', 'force', 'off'],
                capture_output=True, timeout=5
            )
            
            # Trigger screensaver/blank
            subprocess.run(
                ['xset', '-display', self.x_display, 's', 'activate'],
                capture_output=True, timeout=5
            )
            
            self.is_sleeping = True
            logger.info("[SCREEN] Screen put to sleep")
            
            return {'success': True, 'message': 'Screen sleeping'}
            
        except Exception as e:
            logger.error(f"[SCREEN] Error sleeping: {e}")
            return {'success': False, 'error': str(e)}
    
    def wake(self) -> Dict:
        """Wake screen from sleep"""
        try:
            if not self.is_sleeping:
                return {'success': True, 'message': 'Not sleeping'}
            
            # Restore brightness
            brightness_to_restore = getattr(self, '_pre_sleep_brightness', self.brightness)
            self.set_brightness(brightness_to_restore)
            
            # Wake display
            subprocess.run(
                ['xset', '-display', self.x_display, 'dpms', 'force', 'on'],
                capture_output=True, timeout=5
            )
            
            # Reset screensaver
            subprocess.run(
                ['xset', '-display', self.x_display, 's', 'reset'],
                capture_output=True, timeout=5
            )
            
            self.is_sleeping = False
            self.last_activity = time.time()
            
            logger.info("[SCREEN] Screen woke up")
            
            return {'success': True, 'message': 'Screen woke up'}
            
        except Exception as e:
            logger.error(f"[SCREEN] Error waking: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_settings(self, settings: Dict):
        """Update screen settings"""
        if 'screen_brightness' in settings:
            self.set_brightness(settings['screen_brightness'])
        
        if 'screen_sleep_seconds' in settings:
            self.sleep_after_seconds = settings['screen_sleep_seconds']
        
        if 'screen_sleep_enabled' in settings:
            self.sleep_enabled = settings['screen_sleep_enabled']
        
        self.settings.update(settings)
        logger.info(f"[SCREEN] Settings updated: {settings}")
    
    def get_status(self) -> Dict:
        """Get screen status"""
        return {
            'brightness': self.get_brightness(),
            'is_sleeping': self.is_sleeping,
            'sleep_enabled': self.sleep_enabled,
            'sleep_after_seconds': self.sleep_after_seconds,
            'backlight_available': self.backlight_path is not None
        }
