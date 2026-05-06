
"""
Base Broker Class
Abstract base class for all broker implementations
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseBroker(ABC):
    """Abstract base class for broker implementations"""
    
    def __init__(self, name: str):
        self.name = name
        self._connected = False
        self._error = None
        self._client = None
    
    @property
    def connected(self) -> bool:
        """Check if broker is connected (auto-connect if configured)"""
        if not self._connected and self.is_configured():
            try:
                self.connect()
            except Exception as e:
                logger.warning(f"[{self.name}] Auto-connect failed: {e}")
        return self._connected
    
    @property
    def error(self) -> str:
        """Get last error message"""
        return self._error
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API keys are configured"""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to broker API"""
        pass
    
    @abstractmethod
    def get_balance(self) -> float:
        """Get account balance"""
        pass
    
    @abstractmethod
    def get_positions(self) -> list:
        """Get open positions"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> dict:
        """Get account information"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: float, 
                    order_type: str = 'market', limit_price: float = None) -> dict:
        """Place an order"""
        pass
