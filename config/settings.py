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
        # Handle password hashing
        if key == 'password' and value:
            import hashlib
            self._cache['password_hash'] = hashlib.sha256(value.encode()).hexdigest()
        
        self._cache[key] = value
        return self.save()
    
    def update(self, updates):
        """Update multiple settings at once"""
        self._cache.update(updates)
        return self.save()
    
    def get_safe(self):
        """Get settings with sensitive data masked"""
        safe = self._cache.copy()
        sensitive_keys = [
            'alpaca_secret', 'binance_secret', 'ig_password',
            'ibkr_password', 'paypal_client_secret'
        ]
        for key in sensitive_keys:
            if safe.get(key):
                safe[key] = '*' * 10
        return safe
    
    def is_configured(self, broker):
        """Check if a broker is configured"""
        configs = {
            'alpaca': ['alpaca_key', 'alpaca_secret'],
            'binance': ['binance_key', 'binance_secret'],
            'ig': ['ig_api_key', 'ig_username', 'ig_password'],
            'ibkr': ['ibkr_account_id', 'ibkr_username', 'ibkr_password']
        }
        keys = configs.get(broker, [])
        return all(self._cache.get(k) for k in keys)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against stored hash"""
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        stored_hash = self._cache.get('password_hash')
        stored_password = self._cache.get('password')
        
        return hashed == stored_hash or password == stored_password
    
    def change_password(self, new_password: str) -> bool:
        """Change the login password"""
        import hashlib
        self._cache['password_hash'] = hashlib.sha256(new_password.encode()).hexdigest()
        # Clear plaintext password if it exists
        if 'password' in self._cache:
            del self._cache['password']
        return self.save()
    
    def all(self):
        """Get all settings"""
        return self._cache.copy()
