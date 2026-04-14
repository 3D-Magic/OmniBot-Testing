"""
Alpaca Broker Configuration
Handles connection to Alpaca Trading API with live order execution
"""
import logging
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class AlpacaConfig(BaseBroker):
    """Alpaca API wrapper with full trading capability"""
    
    def __init__(self, api_key=None, secret_key=None, paper=True):
        super().__init__('alpaca')
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self._account = None
        
        # Check if alpaca-py is available
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient
            self._client_class = TradingClient
            self._data_client_class = StockHistoricalDataClient
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
            # Initialize data client for market data
            self._data_client = self._data_client_class(self.api_key, self.secret_key)
            
            # Test connection by getting account
            self._account = self._client.get_account()
            self._connected = True
            self._error = None
            
            mode = "PAPER" if self.paper else "LIVE"
            logger.info(f"[ALPACA] Connected ({mode}). Balance: ${float(self._account.portfolio_value):,.2f}")
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
                    'avg_entry_price': float(p.avg_entry_price) if hasattr(p, 'avg_entry_price') else 0.0,
                    'current_price': float(p.current_price) if hasattr(p, 'current_price') else 0.0,
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
    
    def place_order(self, symbol: str, side: str, quantity: float, 
                    order_type: str = 'market', limit_price: float = None) -> dict:
        """
        Place a real order with Alpaca - EXECUTES LIVE TRADES
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            side: 'buy' or 'sell'
            quantity: Number of shares
            order_type: 'market', 'limit', 'stop'
            limit_price: Price for limit orders
            
        Returns:
            dict with order details or None on failure
        """
        if not self._connected:
            logger.error("[ALPACA ORDER] Not connected")
            return None
        
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce
            
            # Map side to Alpaca enum
            alpaca_side = AlpacaOrderSide.BUY if side.lower() == 'buy' else AlpacaOrderSide.SELL
            
            # Create appropriate order request
            if order_type.lower() == 'market':
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY
                )
            elif order_type.lower() == 'limit' and limit_price:
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price
                )
            else:
                logger.error(f"[ALPACA ORDER] Invalid order type: {order_type}")
                return None
            
            # SUBMIT THE ORDER TO ALPACA
            order = self._client.submit_order(order_request)
            
            mode = "PAPER" if self.paper else "LIVE"
            logger.info(f"[ALPACA {mode} ORDER] {side.upper()} {quantity} {symbol} - ID: {order.id}")
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'side': side,
                'quantity': quantity,
                'type': order_type,
                'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
                'broker': 'alpaca',
                'timestamp': order.submitted_at.isoformat() if hasattr(order, 'submitted_at') and order.submitted_at else None
            }
            
        except Exception as e:
            logger.error(f"[ALPACA ORDER ERROR] {e}")
            return None
    
    def get_latest_quote(self, symbol: str) -> dict:
        """Get latest quote for a symbol - REAL MARKET DATA"""
        if not self._connected:
            return {}
        
        try:
            from alpaca.data.requests import StockLatestQuoteRequest
            
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self._data_client.get_stock_latest_quote(request)
            
            if symbol in quotes:
                quote = quotes[symbol]
                return {
                    'symbol': symbol,
                    'bid': float(quote.bid_price),
                    'ask': float(quote.ask_price),
                    'bid_size': float(quote.bid_size),
                    'ask_size': float(quote.ask_size),
                    'timestamp': quote.timestamp.isoformat() if hasattr(quote, 'timestamp') else None
                }
            return {}
            
        except Exception as e:
            logger.error(f"[ALPACA QUOTE ERROR] {symbol}: {e}")
            return {}
    
    def get_latest_trade(self, symbol: str) -> dict:
        """Get latest trade price for a symbol"""
        if not self._connected:
            return {}
        
        try:
            from alpaca.data.requests import StockLatestTradeRequest
            
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self._data_client.get_stock_latest_trade(request)
            
            if symbol in trades:
                trade = trades[symbol]
                return {
                    'symbol': symbol,
                    'price': float(trade.price),
                    'size': float(trade.size),
                    'timestamp': trade.timestamp.isoformat() if hasattr(trade, 'timestamp') else None
                }
            return {}
            
        except Exception as e:
            logger.error(f"[ALPACA TRADE ERROR] {symbol}: {e}")
            return {}
    
    def get_bars(self, symbol: str, timeframe: str = '1Day', limit: int = 100):
        """Get historical price bars for technical analysis"""
        if not self._connected:
            return None
        
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            # Map timeframe string to TimeFrame
            tf_map = {
                '1Min': TimeFrame.Minute,
                '5Min': TimeFrame(5, TimeFrame.Minute),
                '15Min': TimeFrame(15, TimeFrame.Minute),
                '1Hour': TimeFrame.Hour,
                '1Day': TimeFrame.Day
            }
            
            tf = tf_map.get(timeframe, TimeFrame.Day)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                limit=limit
            )
            
            bars = self._data_client.get_stock_bars(request)
            
            if symbol in bars:
                return bars[symbol].df
            return None
            
        except Exception as e:
            logger.error(f"[ALPACA BARS ERROR] {symbol}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        if not self._connected:
            return False
        
        try:
            self._client.cancel_order_by_id(order_id)
            logger.info(f"[ALPACA] Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"[ALPACA CANCEL ERROR] {e}")
            return False
    
    def get_orders(self, status: str = 'open') -> list:
        """Get orders"""
        if not self._connected:
            return []
        
        try:
            from alpaca.trading.enums import QueryOrderStatus
            
            if status.lower() == 'open':
                orders = self._client.get_orders(filter=QueryOrderStatus.OPEN)
            elif status.lower() == 'closed':
                orders = self._client.get_orders(filter=QueryOrderStatus.CLOSED)
            else:
                orders = self._client.get_orders()
            
            return [
                {
                    'id': o.id,
                    'symbol': o.symbol,
                    'qty': float(o.qty),
                    'side': o.side.value if hasattr(o.side, 'value') else str(o.side),
                    'status': o.status.value if hasattr(o.status, 'value') else str(o.status),
                    'submitted_at': o.submitted_at.isoformat() if hasattr(o, 'submitted_at') and o.submitted_at else None
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"[ALPACA GET ORDERS ERROR] {e}")
            return []
