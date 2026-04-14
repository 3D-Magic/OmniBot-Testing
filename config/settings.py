"""
Settings Manager
Handles loading and saving of application settings
"""
import json
import os
import logging
from .constants import SETTINGS_FILE, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


class Settings:
    """Settings manager with file persistence"""
    
    def __init__(self, filepath=None):
        self.filepath = filepath or SETTINGS_FILE
        self._cache = None
        self._load()
    
    def _load(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    loaded = json.load(f)
                # Merge with defaults
                self._cache = DEFAULT_SETTINGS.copy()
                self._cache.update(loaded)
            else:
                self._cache = DEFAULT_SETTINGS.copy()
                self.save()  # Create default settings file
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._cache = DEFAULT_SETTINGS.copy()
    
    def save(self):
        """Save settings to file"""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self._cache, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self._cache.get(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self._cache[key] = value
        return self.save()
    
    def is_configured(self, broker: str) -> bool:
        """Check if a broker is configured"""
        broker_config = self._cache.get(broker, {})
        # Handle different credential formats
        if broker == 'paypal':
            return bool(broker_config.get('client_id') and broker_config.get('client_secret'))
        return bool(broker_config.get('api_key') and broker_config.get('secret_key'))
    
    def get_broker_config(self, broker: str) -> dict:
        """Get broker configuration"""
        return self._cache.get(broker, {})
    
    def set_broker_config(self, broker: str, config: dict):
        """Set broker configuration"""
        self._cache[broker] = config
        return self.save()
    
    def get_all(self) -> dict:
        """Get all settings"""
        return self._cache.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self._cache = DEFAULT_SETTINGS.copy()
        return self.save()
