"""
Binance Broker Configuration
Handles connection to Binance API with live order execution
"""
import logging
from .base_broker import BaseBroker

logger = logging.getLogger(__name__)


class BinanceConfig(BaseBroker):
    """Binance API wrapper with full trading capability"""
    
    def __init__(self, api_key=None, secret_key=None, testnet=True):
        super().__init__('binance')
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self._client = None
        
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
            
            # Test connection by getting account
            account = self._client.get_account()
            self._connected = True
            self._error = None
            
            # Get balance for logging
            total_usdt = sum(float(b['free']) + float(b['locked']) 
                           for b in account['balances'] if b['asset'] == 'USDT')
            
            mode = "TESTNET" if self.testnet else "LIVE"
            logger.info(f"[BINANCE] Connected ({mode}). USDT Balance: ${total_usdt:,.2f}")
            return True
            
        except Exception as e:
            self._error = str(e)
            self._connected = False
            logger.error(f"[BINANCE ERROR] {e}")
            return False
    
    def get_balance(self) -> float:
        """Get total portfolio value in USDT"""
        if not self._connected:
            if not self.connect():
                return 0.0
        
        try:
            account = self._client.get_account()
            
            # Calculate total value in USDT
            total_value = 0.0
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    if asset == 'USDT':
                        total_value += total
                    else:
                        # Get price in USDT
                        try:
                            ticker = self._client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                            total_value += total * price
                        except:
                            pass
            
            return total_value
            
        except Exception as e:
            logger.error(f"[BINANCE BALANCE ERROR] {e}")
            return 0.0
    
    def get_all_balances(self) -> dict:
        """Get all asset balances"""
        if not self._connected:
            return {}
        
        try:
            account = self._client.get_account()
            balances = {}
            
            for b in account['balances']:
                asset = b['asset']
                free = float(b['free'])
                locked = float(b['locked'])
                if free > 0 or locked > 0:
                    balances[asset] = free + locked
            
            return balances
            
        except Exception as e:
            logger.error(f"[BINANCE BALANCES ERROR] {e}")
            return {}
    
    def get_positions(self) -> list:
        """Get open positions (non-zero balances)"""
        if not self._connected:
            return []
        
        try:
            balances = self.get_all_balances()
            positions = []
            
            for asset, amount in balances.items():
                if asset != 'USDT' and amount > 0:
                    try:
                        ticker = self._client.get_symbol_ticker(symbol=f"{asset}USDT")
                        price = float(ticker['price'])
                        
                        positions.append({
                            'symbol': f"{asset}USDT",
                            'qty': amount,
                            'current_price': price,
                            'market_value': amount * price
                        })
                    except:
                        pass
            
            return positions
            
        except Exception as e:
            logger.error(f"[BINANCE POSITIONS ERROR] {e}")
            return []
    
    def get_account_info(self) -> dict:
        """Get full account information"""
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
        """
        Place a real order with Binance - EXECUTES LIVE TRADES
        """
        if not self._connected:
            logger.error("[BINANCE ORDER] Not connected")
            return None
        
        try:
            # Format quantity based on symbol
            if 'BTC' in symbol:
                quantity = round(quantity, 5)
            else:
                quantity = round(quantity, 4)
            
            if quantity <= 0:
                logger.error(f"[BINANCE ORDER] Invalid quantity: {quantity}")
                return None
            
            # Place order
            if order_type.lower() == 'market':
                if side.lower() == 'buy':
                    order = self._client.order_market_buy(symbol=symbol, quantity=quantity)
                else:
                    order = self._client.order_market_sell(symbol=symbol, quantity=quantity)
            elif order_type.lower() == 'limit' and limit_price:
                if side.lower() == 'buy':
                    order = self._client.order_limit_buy(
                        symbol=symbol, quantity=quantity, price=limit_price)
                else:
                    order = self._client.order_limit_sell(
                        symbol=symbol, quantity=quantity, price=limit_price)
            else:
                logger.error(f"[BINANCE ORDER] Invalid order type: {order_type}")
                return None
            
            mode = "TESTNET" if self.testnet else "LIVE"
            logger.info(f"[BINANCE {mode} ORDER] {side.upper()} {quantity} {symbol} - ID: {order['orderId']}")
            
            return {
                'id': str(order['orderId']),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'type': order_type,
                'status': order['status'],
                'broker': 'binance',
                'timestamp': order['transactTime']
            }
            
        except Exception as e:
            logger.error(f"[BINANCE ORDER ERROR] {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for a symbol"""
        if not self._connected:
            return 0.0
        
        try:
            ticker = self._client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"[BINANCE PRICE ERROR] {symbol}: {e}")
            return 0.0
    
    def get_klines(self, symbol: str, interval: str = '1d', limit: int = 100):
        """Get historical klines/candles for technical analysis"""
        if not self._connected:
            return None
        
        try:
            import pandas as pd
            
            klines = self._client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"[BINANCE KLINES ERROR] {symbol}: {e}")
            return None
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an open order"""
        if not self._connected:
            return False
        
        try:
            self._client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"[BINANCE] Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"[BINANCE CANCEL ERROR] {e}")
            return False
    
    def get_orders(self, symbol: str = None) -> list:
        """Get open orders"""
        if not self._connected:
            return []
        
        try:
            if symbol:
                orders = self._client.get_open_orders(symbol=symbol)
            else:
                orders = self._client.get_open_orders()
            
            return [
                {
                    'id': str(o['orderId']),
                    'symbol': o['symbol'],
                    'qty': float(o['origQty']),
                    'side': o['side'],
                    'status': o['status']
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"[BINANCE GET ORDERS ERROR] {e}")
            return []
