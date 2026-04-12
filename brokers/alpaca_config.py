"""
Alpaca Broker Configuration
Handles connection to Alpaca Trading API
"""

import logging
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class AlpacaConfig(BaseBroker):
    """Alpaca API wrapper"""
    
    def __init__(self, api_key=None, secret_key=None, paper=True):
        super().__init__('alpaca')
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self._account = None
        
        # Check if alpaca-py is available
        try:
            from alpaca.trading.client import TradingClient
            self._client_class = TradingClient
            self._available = True
        except ImportError:
            logger.warning("Alpaca API not installed. Run: pip install alpaca-py")
            self._available = False
    
    def is_configured(self) -> bool:
        """Check if API keys are configured"""
        return bool(self.api_key and self.secret_key)
    
    def connect(self) -> bool:
        """Connect to Alpaca API"""
        if not self._available:
            self._error = "Alpaca library not installed"
            return False
        
        if not self.is_configured():
            self._error = "API keys not configured"
            return False
        
        try:
            self._client = self._client_class(
                self.api_key, 
                self.secret_key, 
                paper=self.paper
            )
            # Test connection by getting account
            self._account = self._client.get_account()
            self._connected = True
            self._error = None
            logger.info(f"[ALPACA] Connected. Balance: ${self._account.portfolio_value}")
            return True
            
        except Exception as e:
            self._error = str(e)
            self._connected = False
            logger.error(f"[ALPACA ERROR] {e}")
            return False
    
    def get_balance(self) -> float:
        """Get account portfolio value"""
        if not self._connected:
            if not self.connect():
                return 0.0
        
        try:
            self._account = self._client.get_account()
            return float(self._account.portfolio_value)
        except Exception as e:
            self._error = str(e)
            logger.error(f"[ALPACA BALANCE ERROR] {e}")
            return 0.0
    
    def get_positions(self) -> list:
        """Get open positions"""
        if not self._connected:
            return []
        
        try:
            positions = self._client.get_all_positions()
            return [
                {
                    'symbol': p.symbol,
                    'qty': int(p.qty) if hasattr(p, 'qty') else int(p.quantity),
                    'market_value': float(p.market_value) if hasattr(p, 'market_value') else 0.0,
                    'unrealized_pl': float(p.unrealized_pl) if hasattr(p, 'unrealized_pl') else 0.0
                }
                for p in positions
            ]
        except Exception as e:
            logger.error(f"[ALPACA POSITIONS ERROR] {e}")
            return []
    
    def get_account_info(self) -> dict:
        """Get full account information"""
        if not self._connected:
            return {}
        
        try:
            account = self._client.get_account()
            return {
                'balance': float(account.portfolio_value),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'positions': self.get_positions(),
                'status': 'connected'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = 'market') -> dict:
        """Place a real order with Alpaca"""
        if not self._connected:
            logger.error("[ALPACA ORDER] Not connected")
            return None
        
        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce
            
            # Map side to Alpaca enum
            alpaca_side = AlpacaOrderSide.BUY if side.lower() == 'buy' else AlpacaOrderSide.SELL
            
            # Create order request
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=alpaca_side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self._client.submit_order(order_request)
            
            logger.info(f"[ALPACA ORDER] {side.upper()} {quantity} {symbol} - ID: {order.id}")
            
            return {
                'id': order.id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'status': order.status,
                'broker': 'alpaca'
            }
            
        except Exception as e:
            logger.error(f"[ALPACA ORDER ERROR] {e}")
            return None
