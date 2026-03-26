"""
OMNIBOT v2.7 Titan - Forex Trading Engine (OANDA)
Supports 90+ currency pairs, metals, and CFDs
"""

import logging
from typing import Dict, List, Optional

try:
    import v20
except ImportError:
    v20 = None

logger = logging.getLogger(__name__)


class ForexEngine:
    """Forex trading engine using OANDA v20 API"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.ctx = None
        self.account_id = None
        
        if not self.enabled or v20 is None:
            logger.warning("Forex engine disabled or v20 not installed")
            return
        
        try:
            # Parse hostname from base_url
            hostname = config['base_url'].replace('https://', '').replace('http://', '')
            
            self.ctx = v20.Context(
                hostname=hostname,
                token=config['access_token']
            )
            self.account_id = config['account_id']
            
            # Test connection
            response = self.ctx.account.get(self.account_id)
            account = response.body['account']
            
            env = config.get('environment', 'practice')
            logger.info(f"✅ OANDA connected ({env})")
            logger.info(f"   Balance: ${float(account.NAV):,.2f}")
            
        except Exception as e:
            logger.error(f"❌ OANDA connection failed: {e}")
            self.enabled = False
    
    def is_connected(self) -> bool:
        """Check if connected to OANDA"""
        return self.ctx is not None and self.enabled
    
    def get_balance(self) -> Dict:
        """Get account balance"""
        if not self.is_connected():
            return {'total': 0.0, 'available': 0.0, 'currency': 'USD'}
        
        try:
            response = self.ctx.account.get(self.account_id)
            account = response.body['account']
            
            return {
                'total': float(account.NAV),
                'available': float(account.marginAvailable),
                'currency': account.currency,
                'margin_used': float(account.marginUsed),
                'unrealized_pl': float(account.unrealizedPL)
            }
            
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return {'total': 0.0, 'available': 0.0, 'currency': 'USD'}
    
    def get_price(self, instrument: str) -> Dict:
        """Get current price for an instrument"""
        if not self.is_connected():
            return {'bid': 0.0, 'ask': 0.0, 'spread': 0.0}
        
        try:
            response = self.ctx.pricing.get(
                self.account_id,
                instruments=instrument
            )
            price = response.body['prices'][0]
            
            bid = float(price.bids[0].price) if price.bids else 0
            ask = float(price.asks[0].price) if price.asks else 0
            
            return {
                'bid': bid,
                'ask': ask,
                'spread': ask - bid,
                'instrument': instrument
            }
            
        except Exception as e:
            logger.error(f"Price error for {instrument}: {e}")
            return {'bid': 0.0, 'ask': 0.0, 'spread': 0.0}
    
    def place_order(self, instrument: str, units: int, side: str) -> Dict:
        """Place a forex order"""
        if not self.is_connected():
            return {'success': False, 'error': 'Not connected'}
        
        try:
            # OANDA uses positive units for buy, negative for sell
            order_units = units if side == 'buy' else -units
            
            response = self.ctx.order.market(
                self.account_id,
                instrument=instrument,
                units=order_units
            )
            
            logger.info(f"✅ Forex order: {side} {units} {instrument}")
            return {
                'success': True,
                'order_id': response.body['orderFillTransaction'].id,
                'instrument': instrument,
                'units': units,
                'side': side
            }
            
        except Exception as e:
            logger.error(f"Order error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_open_positions(self) -> List[Dict]:
        """Get open positions"""
        if not self.is_connected():
            return []
        
        try:
            response = self.ctx.position.list(self.account_id)
            positions = []
            
            for pos in response.body['positions']:
                long_units = sum(t.units for t in pos.long.tradeIDs) if pos.long else 0
                short_units = sum(t.units for t in pos.short.tradeIDs) if pos.short else 0
                
                if long_units != 0 or short_units != 0:
                    positions.append({
                        'instrument': pos.instrument,
                        'long_units': long_units,
                        'short_units': short_units,
                        'net_units': long_units + short_units
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []