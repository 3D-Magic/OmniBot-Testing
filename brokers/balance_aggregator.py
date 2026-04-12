"""
Balance Aggregator
Combines balances from all configured brokers
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BalanceAggregator:
    """Aggregates balances from multiple brokers"""
    
    def __init__(self):
        self._brokers: Dict[str, object] = {}
        self._cache = {
            'total_capital': 0.0,
            'stocks': 0.0,
            'crypto': 0.0,
            'forex': 0.0,
            'last_update': None
        }
    
    def add_broker(self, name: str, broker):
        """Add a broker to the aggregator"""
        self._brokers[name] = broker
        logger.info(f"[AGGREGATOR] Added broker: {name}")
    
    def remove_broker(self, name: str):
        """Remove a broker from the aggregator"""
        if name in self._brokers:
            del self._brokers[name]
            logger.info(f"[AGGREGATOR] Removed broker: {name}")
    
    def get_broker(self, name: str):
        """Get a specific broker instance"""
        return self._brokers.get(name)
    
    def get_all_brokers(self) -> Dict[str, object]:
        """Get all broker instances"""
        return self._brokers.copy()
    
    def get_all_balances(self, force_refresh=False, demo_mode=False) -> dict:
        """Get balances from all configured brokers"""
        result = {
            'total_capital': 0.0,
            'stocks': 0.0,
            'crypto': 0.0,
            'forex': 0.0,
            'broker_data': {},
            'last_update': datetime.now().isoformat()
        }
        
        # If demo mode or no brokers configured, return demo values
        if demo_mode or len(self._brokers) == 0:
            result.update({
                'total_capital': 100000.0,
                'stocks': 40000.0,
                'crypto': 35000.0,
                'forex': 25000.0,
                'is_demo': True
            })
            return result
        
        # Map broker names to asset types
        asset_types = {
            'alpaca': 'stocks',
            'binance': 'crypto',
            'ibkr': 'forex',
            'ig': 'forex'
        }
        
        for name, broker in self._brokers.items():
            broker_result = {
                'configured': broker.is_configured(),
                'connected': False,
                'balance': 0.0,
                'error': None
            }
            
            if broker.is_configured():
                try:
                    balance = broker.get_balance()
                    broker_result['balance'] = balance
                    broker_result['connected'] = broker.connected
                    
                    # Add to appropriate category
                    asset_type = asset_types.get(name, 'other')
                    result[asset_type] += balance
                    result['total_capital'] += balance
                    
                except Exception as e:
                    broker_result['error'] = str(e)
                    logger.error(f"[AGGREGATOR] Error getting balance from {name}: {e}")
            else:
                broker_result['error'] = 'Not configured'
            
            result['broker_data'][name] = broker_result
        
        # Update cache
        self._cache = result.copy()
        
        return result
    
    def get_total_capital(self) -> float:
        """Get total capital across all brokers"""
        balances = self.get_all_balances()
        return balances['total_capital']
    
    def get_broker_status(self) -> dict:
        """Get connection status of all brokers"""
        return {
            name: broker.get_status()
            for name, broker in self._brokers.items()
        }
    
    def connect_all(self) -> dict:
        """Connect to all configured brokers"""
        results = {}
        for name, broker in self._brokers.items():
            if broker.is_configured():
                success = broker.connect()
                results[name] = {
                    'success': success,
                    'error': broker.error if not success else None
                }
            else:
                results[name] = {'success': False, 'error': 'Not configured'}
        return results
    
    def disconnect_all(self):
        """Disconnect from all brokers"""
        for broker in self._brokers.values():
            broker.disconnect()
        logger.info("[AGGREGATOR] Disconnected from all brokers")
    
    def get_cached_data(self) -> dict:
        """Get cached balance data"""
        return self._cache.copy()
