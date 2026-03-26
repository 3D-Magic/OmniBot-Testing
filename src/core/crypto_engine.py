"""
OMNIBOT v2.7 Titan - Crypto Trading Engine (CCXT)
Supports 100+ exchanges: Binance, Coinbase, Kraken, etc.
"""

import logging
from typing import Dict, List, Optional

try:
    import ccxt
except ImportError:
    ccxt = None

logger = logging.getLogger(__name__)


class CryptoEngine:
    """Cryptocurrency trading engine via CCXT"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.exchange = None
        
        if not self.enabled or ccxt is None:
            logger.warning("Crypto engine disabled or ccxt not installed")
            return
        
        try:
            exchange_name = config.get('exchange', 'binance')
            exchange_class = getattr(ccxt, exchange_name)
            
            # Initialize exchange
            self.exchange = exchange_class({
                'apiKey': config.get('api_key'),
                'secret': config.get('secret'),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
            
            # Enable testnet/sandbox if configured
            if config.get('testnet', True):
                self.exchange.set_sandbox_mode(True)
                logger.info("✅ Crypto connected (Testnet)")
            else:
                logger.info("✅ Crypto connected (Live)")
                
        except Exception as e:
            logger.error(f"❌ Crypto connection failed: {e}")
            self.enabled = False
    
    def is_connected(self) -> bool:
        """Check if connected to exchange"""
        return self.exchange is not None and self.enabled
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value in USD"""
        if not self.is_connected():
            return 0.0
        
        try:
            balance = self.exchange.fetch_balance()
            total = balance.get('total', {})
            
            # Calculate total USD value
            usdt_value = total.get('USDT', 0)
            btc_price = self.exchange.fetch_ticker('BTC/USDT')['last']
            btc_value = total.get('BTC', 0) * btc_price
            eth_price = self.exchange.fetch_ticker('ETH/USDT')['last']
            eth_value = total.get('ETH', 0) * eth_price
            
            return usdt_value + btc_value + eth_value
            
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 0.0
    
    def get_balance(self) -> Dict:
        """Get account balance"""
        if not self.is_connected():
            return {'total': 0.0, 'free': 0.0, 'used': 0.0}
        
        try:
            balance = self.exchange.fetch_balance()
            return {
                'total': balance.get('total', {}).get('USDT', 0),
                'free': balance.get('free', {}).get('USDT', 0),
                'used': balance.get('used', {}).get('USDT', 0)
            }
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return {'total': 0.0, 'free': 0.0, 'used': 0.0}
    
    def get_price(self, symbol: str) -> Dict:
        """Get current price for a symbol"""
        if not self.is_connected():
            return {'bid': 0.0, 'ask': 0.0, 'last': 0.0}
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'last': ticker.get('last', 0),
                'change': ticker.get('change', 0),
                'percentage': ticker.get('percentage', 0)
            }
        except Exception as e:
            logger.error(f"Price error for {symbol}: {e}")
            return {'bid': 0.0, 'ask': 0.0, 'last': 0.0}
    
    def place_order(self, symbol: str, side: str, amount: float, 
                    order_type: str = 'market') -> Dict:
        """Place a crypto order"""
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected'}
        
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount
            )
            
            logger.info(f"✅ Crypto order: {side} {amount} {symbol}")
            return {
                'success': True,
                'order_id': order.get('id'),
                'status': order.get('status'),
                'symbol': symbol,
                'side': side,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"Order error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_positions(self) -> List[Dict]:
        """Get open positions (balances)"""
        if not self.is_connected():
            return []
        
        try:
            balance = self.exchange.fetch_balance()
            positions = []
            
            for currency, amount in balance.get('total', {}).items():
                if amount > 0 and currency != 'USDT':
                    positions.append({
                        'symbol': f"{currency}/USDT",
                        'size': amount,
                        'side': 'LONG',
                        'entry_price': 0,  # Would need trade history
                        'current_price': self.get_price(f"{currency}/USDT")['last']
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []