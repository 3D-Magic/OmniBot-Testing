"""
import concurrent.futures
Balance Aggregator
Aggregates balances from multiple brokers
"""
import concurrent.futures
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class BalanceAggregator:
    """Aggregates account information from multiple brokers"""
    
    def __init__(self):
        self.brokers: Dict[str, object] = {}
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 5  # 5 second cache
    
    def add_broker(self, name: str, broker: object):
        """Add a broker to the aggregator"""
        self.brokers[name] = broker
        logger.info(f"[AGGREGATOR] Added broker: {name}")
    
    def remove_broker(self, name: str):
        """Remove a broker from the aggregator"""
        if name in self.brokers:
            del self.brokers[name]
            logger.info(f"[AGGREGATOR] Removed broker: {name}")
    
    def get_broker(self, name: str) -> object:
        """Get a specific broker"""
        return self.brokers.get(name)
    
    def get_all_brokers(self) -> Dict[str, object]:
        """Get all brokers"""
        return self.brokers
    
    def connect_all(self):
        """Connect to all configured brokers"""
        for name, broker in self.brokers.items():
            if broker.is_configured() and not broker.connected:
                logger.info(f"[AGGREGATOR] Connecting to {name}...")
                broker.connect()
    
    def get_total_capital(self) -> float:
        """Get total capital across all brokers"""
        total = 0.0
        for name, broker in self.brokers.items():
            if broker.connected:
                try:
                    balance = broker.get_balance()
                    total += balance
                except Exception as e:
                    logger.error(f"[AGGREGATOR] Error getting balance from {name}: {e}")
        return total
    
    def get_all_positions(self) -> List[dict]:
        """Get all positions across all brokers"""
        all_positions = []
        for name, broker in self.brokers.items():
            if broker.connected:
                try:
                    positions = broker.get_positions()
                    for pos in positions:
                        pos['broker'] = name
                    all_positions.extend(positions)
                except Exception as e:
                    logger.error(f"[AGGREGATOR] Error getting positions from {name}: {e}")
        return all_positions
    
    def get_portfolio_summary(self) -> dict:
        """Get portfolio summary across all brokers"""
        summary = {
            'total_capital': 0.0,
            'positions': [],
            'brokers': {}
        }
        
        for name, broker in self.brokers.items():
            if not broker.connected:
                summary['brokers'][name] = {'connected': False}
                continue
            
            def fetch_broker_data(b):
                return b.get_balance(), b.get_positions()
            
            try:
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = executor.submit(fetch_broker_data, broker)
                try:
                    balance, positions = future.result(timeout=8)
                    executor.shutdown(wait=False)
                except concurrent.futures.TimeoutError:
                    executor.shutdown(wait=False)
                    logger.error(f"[AGGREGATOR] Timeout fetching data from {name}")
                    summary['brokers'][name] = {
                        'connected': False,
                        'error': 'Timeout fetching data'
                    }
                    continue
                
                summary['total_capital'] += balance
                summary['positions'].extend(positions)
                summary['brokers'][name] = {
                    'balance': balance,
                    'positions_count': len(positions),
                    'connected': True
                }
            except Exception as e:
                logger.error(f"[AGGREGATOR] Error getting summary from {name}: {e}")
                summary['brokers'][name] = {
                    'connected': False,
                    'error': str(e)
                }
        
        return summary
    def get_status(self) -> dict:
        """Get status of all brokers"""
        status = {}
        for name, broker in self.brokers.items():
            status[name] = {
                'configured': broker.is_configured(),
                'connected': broker.connected,
                'error': broker.error
            }
        return status
