"""
Base Broker Interface
All broker implementations must inherit from this class
"""

from abc import ABC, abstractmethod


class BaseBroker(ABC):
    """Abstract base class for all brokers"""
    
    def __init__(self, name):
        self.name = name
        self._connected = False
        self._client = None
        self._error = None
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker API"""
        pass
    
    @abstractmethod
    def get_balance(self) -> float:
        """Get account balance"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if broker has required configuration"""
        pass
    
    @property
    def connected(self) -> bool:
        """Connection status"""
        return self._connected
    
    @property
    def error(self) -> str:
        """Last error message"""
        return self._error
    
    def disconnect(self):
        """Disconnect from broker"""
        self._connected = False
        self._client = None
    
    def get_status(self) -> dict:
        """Get broker status"""
        return {
            'name': self.name,
            'connected': self._connected,
            'configured': self.is_configured(),
            'error': self._error
        }
