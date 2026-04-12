"""
IG Markets Configuration
Forex and CFD trading broker integration
"""

import logging
from typing import Dict, Optional
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class IGConfig(BaseBroker):
    """IG Markets broker configuration"""
    
    def __init__(self, api_key: str = None, username: str = None, password: str = None, 
                 account_id: str = None, demo: bool = True):
        self.api_key = api_key or ''
        self.username = username or ''
        self.password = password or ''
        self.account_id = account_id or ''
        self.demo = demo
        self._balance = 0.0
        self._connected = False
        self._client = None
        
    def is_configured(self) -> bool:
        """Check if IG is properly configured"""
        return all([
            self.api_key and len(self.api_key) > 10,
            self.username and len(self.username) > 0,
            self.password and len(self.password) > 0
        ])
    
    def connect(self) -> bool:
        """Connect to IG API"""
        if not self.is_configured():
            logger.warning("[IG] Not configured - cannot connect")
            return False
        
        try:
            # Try to import trading_ig library
            try:
                from trading_ig import IGService
            except ImportError:
                logger.error("[IG] trading_ig library not installed. Run: pip install trading_ig")
                return False
            
            # Create IG service
            self._client = IGService(
                username=self.username,
                password=self.password,
                api_key=self.api_key,
                acc_type='DEMO' if self.demo else 'LIVE'
            )
            
            # Connect and create session
            self._client.create_session()
            
            # Verify connection by fetching accounts
            accounts = self._client.fetch_accounts()
            
            if self.account_id:
                # Use specified account
                self._client.switch_account(self.account_id, False)
            
            self._connected = True
            logger.info(f"[IG] Connected to {'DEMO' if self.demo else 'LIVE'} environment")
            return True
            
        except Exception as e:
            logger.error(f"[IG] Connection failed: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from IG"""
        self._connected = False
        self._client = None
        logger.info("[IG] Disconnected")
        return True
    
    def get_balance(self) -> float:
        """Get account balance"""
        if not self._connected or not self._client:
            # Try to connect
            if not self.connect():
                return 0.0
        
        try:
            # Fetch account info
            accounts = self._client.fetch_accounts()
            
            # Get balance from first account or specified account
            for account in accounts['accounts']:
                if not self.account_id or account['accountId'] == self.account_id:
                    balance = float(account.get('balance', {}).get('balance', 0))
                    self._balance = balance
                    return balance
            
            # Fallback to first account
            if accounts['accounts']:
                balance = float(accounts['accounts'][0].get('balance', {}).get('balance', 0))
                self._balance = balance
                return balance
                
        except Exception as e:
            logger.error(f"[IG] Failed to get balance: {e}")
        
        return self._balance
    
    def get_positions(self) -> list:
        """Get open positions"""
        if not self._connected or not self._client:
            return []
        
        try:
            positions = self._client.fetch_open_positions()
            return positions.get('positions', [])
        except Exception as e:
            logger.error(f"[IG] Failed to get positions: {e}")
            return []
    
    def place_order(self, symbol: str, side: str, quantity: float, 
                   order_type: str = 'market', price: float = None) -> Optional[Dict]:
        """Place a forex/CFD order"""
        if not self._connected or not self._client:
            logger.error("[IG] Not connected - cannot place order")
            return None
        
        try:
            # Map symbol to IG epic (e.g., 'EURUSD' -> 'CS.D.EURUSD.CFD.IP')
            epic = self._symbol_to_epic(symbol)
            
            # Determine direction
            direction = 'BUY' if side.upper() == 'BUY' else 'SELL'
            
            # Place order
            response = self._client.create_open_position(
                currency_code='USD',
                direction=direction,
                epic=epic,
                order_type=order_type.upper(),
                expiry='DFB',  # Daily funded bet (rolling)
                force_open=True,
                guaranteed_stop=False,
                size=quantity,
                level=price if order_type.lower() == 'limit' else None
            )
            
            logger.info(f"[IG] Order placed: {direction} {quantity} {symbol}")
            return {
                'order_id': response.get('dealId'),
                'status': 'filled',
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': response.get('level')
            }
            
        except Exception as e:
            logger.error(f"[IG] Order failed: {e}")
            return None
    
    def close_position(self, deal_id: str) -> bool:
        """Close an open position"""
        if not self._connected or not self._client:
            return False
        
        try:
            self._client.close_open_position(deal_id)
            logger.info(f"[IG] Position closed: {deal_id}")
            return True
        except Exception as e:
            logger.error(f"[IG] Close position failed: {e}")
            return False
    
    def _symbol_to_epic(self, symbol: str) -> str:
        """Convert symbol to IG epic format"""
        # Common forex pairs
        epic_map = {
            'EURUSD': 'CS.D.EURUSD.CFD.IP',
            'GBPUSD': 'CS.D.GBPUSD.CFD.IP',
            'USDJPY': 'CS.D.USDJPY.CFD.IP',
            'AUDUSD': 'CS.D.AUDUSD.CFD.IP',
            'USDCAD': 'CS.D.USDCAD.CFD.IP',
            'USDCHF': 'CS.D.USDCHF.CFD.IP',
            'NZDUSD': 'CS.D.NZDUSD.CFD.IP',
            'EURGBP': 'CS.D.EURGBP.CFD.IP',
            'EURJPY': 'CS.D.EURJPY.CFD.IP',
            'GBPJPY': 'CS.D.GBPJPY.CFD.IP',
        }
        
        # Remove any separators and uppercase
        symbol_clean = symbol.upper().replace('/', '').replace('-', '')
        
        return epic_map.get(symbol_clean, symbol)
    
    @property
    def connected(self) -> bool:
        """Connection status"""
        return self._connected
    
    @property
    def name(self) -> str:
        return "IG Markets"
    
    @property
    def asset_type(self) -> str:
        return "forex"
