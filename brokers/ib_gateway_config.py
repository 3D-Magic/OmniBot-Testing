"""
Interactive Brokers Gateway Configuration
Handles connection to IB Gateway (stub - can be expanded)
"""
import logging
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class IBGatewayConfig(BaseBroker):
    """Interactive Brokers Gateway wrapper"""
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        super().__init__('ibkr')
        self.host = host
        self.port = port
        self.client_id = client_id
        self._available = False
        
        try:
            from ib_insync import IB
            self._ib_class = IB
            self._available = True
        except ImportError:
            logger.warning("ib_insync not installed. Run: pip install ib-insync")
    
    def is_configured(self) -> bool:
        """Check if IB Gateway is configured"""
        return True  # Always configured with default values
    
    def connect(self) -> bool:
        """Connect to IB Gateway"""
        if not self._available:
            self._error = "ib_insync not installed"
            return False
        
        try:
            self._client = self._ib_class()
            self._client.connect(self.host, self.port, clientId=self.client_id)
            self._connected = True
            logger.info(f"[IBKR] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            self._error = str(e)
            logger.error(f"[IBKR ERROR] {e}")
            return False
    
    def get_balance(self) -> float:
        """Get account balance"""
        if not self._connected:
            return 0.0
        try:
            account = self._client.accountValues()
            for av in account:
                if av.tag == 'NetLiquidation':
                    return float(av.value)
            return 0.0
        except Exception as e:
            logger.error(f"[IBKR BALANCE ERROR] {e}")
            return 0.0
    
    def get_positions(self) -> list:
        """Get open positions"""
        if not self._connected:
            return []
        try:
            positions = self._client.positions()
            return [
                {
                    'symbol': p.contract.symbol,
                    'qty': p.position,
                    'avg_entry_price': p.avgCost
                }
                for p in positions
            ]
        except Exception as e:
            logger.error(f"[IBKR POSITIONS ERROR] {e}")
            return []
    
    def get_account_info(self) -> dict:
        """Get account information"""
        if not self._connected:
            return {}
        try:
            return {
                'balance': self.get_balance(),
                'positions': self.get_positions(),
                'status': 'connected'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def place_order(self, symbol: str, side: str, quantity: float,
                    order_type: str = 'market', limit_price: float = None) -> dict:
        """Place an order with IBKR"""
        if not self._connected:
            logger.error("[IBKR ORDER] Not connected")
            return None
        
        try:
            from ib_insync import Stock, MarketOrder, LimitOrder
            
            contract = Stock(symbol, 'SMART', 'USD')
            
            if order_type.lower() == 'market':
                order = MarketOrder(side.upper(), quantity)
            elif order_type.lower() == 'limit' and limit_price:
                order = LimitOrder(side.upper(), quantity, limit_price)
            else:
                return None
            
            trade = self._client.placeOrder(contract, order)
            
            return {
                'id': str(trade.order.orderId),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'type': order_type,
                'broker': 'ibkr'
            }
        except Exception as e:
            logger.error(f"[IBKR ORDER ERROR] {e}")
            return None
