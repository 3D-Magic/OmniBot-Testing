"""
Interactive Brokers Gateway Configuration
Handles connection to IB Gateway/TWS
"""

import logging
import os
import subprocess
import time
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class IBGatewayConfig(BaseBroker):
    """IB Gateway/IBKR API wrapper"""
    
    def __init__(self, account_id=None, username=None, password=None, 
                 host='127.0.0.1', port=4002, client_id=1):
        super().__init__('ibkr')
        self.account_id = account_id
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.client_id = client_id
        
        # Check if ib_insync is available
        try:
            from ib_insync import IB
            self._ib_class = IB
            self._available = True
        except ImportError:
            logger.warning("IB API not installed. Run: pip install ib-insync")
            self._available = False
    
    def is_configured(self) -> bool:
        """Check if IB credentials are configured"""
        return bool(self.account_id and self.username and self.password)
    
    def connect(self) -> bool:
        """Connect to IB Gateway"""
        if not self._available:
            self._error = "IB library not installed"
            return False
        
        try:
            from ib_insync import IB
            self._client = IB()
            self._client.connect(self.host, self.port, clientId=self.client_id)
            
            # Test connection
            accounts = self._client.managedAccounts()
            
            self._connected = True
            self._error = None
            logger.info(f"[IBKR] Connected. Accounts: {accounts}")
            return True
            
        except Exception as e:
            self._error = str(e)
            self._connected = False
            logger.error(f"[IBKR ERROR] {e}")
            return False
    
    def get_balance(self) -> float:
        """Get account balance"""
        if not self._connected:
            if not self.connect():
                return 0.0
        
        try:
            # Get account values
            account_values = self._client.accountValues()
            
            # Look for NetLiquidation value
            for av in account_values:
                if av.tag == 'NetLiquidation':
                    return float(av.value)
            
            return 0.0
        except Exception as e:
            self._error = str(e)
            logger.error(f"[IBKR BALANCE ERROR] {e}")
            return 0.0
    
    def start_gateway(self) -> bool:
        """Start IB Gateway (if installed locally)"""
        try:
            # Path to IB Gateway (adjust as needed)
            gateway_paths = [
                '/opt/ibgateway/ibgateway',
                '/usr/local/ibgateway/ibgateway',
                '/home/omnibot/ibgateway/ibgateway'
            ]
            
            for path in gateway_paths:
                if os.path.exists(path):
                    subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info(f"[IBKR] Started gateway from {path}")
                    # Wait for gateway to start
                    time.sleep(10)
                    return True
            
            logger.warning("[IBKR] Gateway executable not found")
            return False
            
        except Exception as e:
            logger.error(f"[IBKR START ERROR] {e}")
            return False
    
    def get_account_info(self) -> dict:
        """Get full account information"""
        if not self._connected:
            return {}
        
        try:
            accounts = self._client.managedAccounts()
            return {
                'balance': self.get_balance(),
                'accounts': accounts,
                'status': 'connected'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def disconnect(self):
        """Disconnect from IB Gateway"""
        if self._client:
            try:
                self._client.disconnect()
            except:
                pass
        self._connected = False
        self._client = None
