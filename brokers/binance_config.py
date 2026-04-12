"""
Binance Broker Configuration
Handles connection to Binance API
"""

import logging
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class BinanceConfig(BaseBroker):
    """Binance API wrapper"""
    
    def __init__(self, api_key=None, secret_key=None, testnet=True):
        super().__init__('binance')
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self._account = None
        
        # Check if python-binance is available
        try:
            from binance.client import Client
            self._client_class = Client
            self._available = True
        except ImportError:
            logger.warning("Binance API not installed. Run: pip install python-binance")
            self._available = False
    
    def is_configured(self) -> bool:
        """Check if API keys are configured"""
        return bool(self.api_key and self.secret_key)
    
    def connect(self) -> bool:
        """Connect to Binance API"""
        if not self._available:
            self._error = "Binance library not installed"
            return False
        
        if not self.is_configured():
            self._error = "API keys not configured"
            return False
        
        try:
            self._client = self._client_class(
                self.api_key, 
                self.secret_key,
                testnet=self.testnet
            )
            # Test connection
            self._account = self._client.get_account()
            self._connected = True
            self._error = None
            logger.info("[BINANCE] Connected successfully")
            return True
            
        except Exception as e:
            self._error = str(e)
            self._connected = False
            logger.error(f"[BINANCE ERROR] {e}")
            return False
    
    def get_balance(self) -> float:
        """Get USDT balance (approximation of portfolio value)"""
        if not self._connected:
            if not self.connect():
                return 0.0
        
        try:
            account = self._client.get_account()
            usdt_balance = sum(
                float(b['free']) + float(b['locked'])
                for b in account['balances']
                if b['asset'] in ['USDT', 'BUSD']
            )
            return usdt_balance
        except Exception as e:
            self._error = str(e)
            logger.error(f"[BINANCE BALANCE ERROR] {e}")
            return 0.0
    
    def get_all_balances(self) -> dict:
        """Get all asset balances"""
        if not self._connected:
            return {}
        
        try:
            account = self._client.get_account()
            return {
                b['asset']: float(b['free']) + float(b['locked'])
                for b in account['balances']
                if float(b['free']) > 0 or float(b['locked']) > 0
            }
        except Exception as e:
            logger.error(f"[BINANCE BALANCES ERROR] {e}")
            return {}
    
    def get_account_info(self) -> dict:
        """Get full account information"""
        if not self._connected:
            return {}
        
        try:
            return {
                'balance': self.get_balance(),
                'all_balances': self.get_all_balances(),
                'status': 'connected'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = 'market') -> dict:
        """Place a real order with Binance"""
        if not self._connected:
            logger.error("[BINANCE ORDER] Not connected")
            return None
        
        try:
            # Ensure symbol format (add USDT if not present)
            if 'USDT' not in symbol and 'BUSD' not in symbol:
                symbol = f"{symbol}USDT"
            
            # Place market order
            if side.lower() == 'buy':
                order = self._client.order_market_buy(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                order = self._client.order_market_sell(
                    symbol=symbol,
                    quantity=quantity
                )
            
            logger.info(f"[BINANCE ORDER] {side.upper()} {quantity} {symbol} - ID: {order['orderId']}")
            
            return {
                'id': str(order['orderId']),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'status': order['status'],
                'broker': 'binance'
            }
            
        except Exception as e:
            logger.error(f"[BINANCE ORDER ERROR] {e}")
            return None
