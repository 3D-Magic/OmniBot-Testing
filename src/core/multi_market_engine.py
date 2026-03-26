"""
OMNIBOT v2.7 Titan - Multi-Market Trading Engine
Orchestrates Stocks (Alpaca) + Crypto (CCXT) + Forex (OANDA)
"""

import logging
import threading
import time
from typing import Dict, List
from datetime import datetime

from config.settings import ALPACA, CRYPTO, FOREX, TRADING, AUTO_TRADER

try:
    from src.core.trading_engine import TradingEngine
except ImportError:
    TradingEngine = None

try:
    from src.core.crypto_engine import CryptoEngine
except ImportError:
    CryptoEngine = None

try:
    from src.core.forex_engine import ForexEngine
except ImportError:
    ForexEngine = None

logger = logging.getLogger(__name__)


class MultiMarketEngine:
    """
    Unified engine managing multiple markets:
    - Stocks via Alpaca
    - Crypto via CCXT (Binance, etc.)
    - Forex via OANDA
    """
    
    def __init__(self):
        self.running = False
        self.lock = threading.Lock()
        
        # Initialize individual engines
        self.stock_engine = None
        self.crypto_engine = None
        self.forex_engine = None
        
        # Portfolio tracking
        self.total_capital = 0.0
        self.initial_capital = TRADING.get('initial_capital', 10000.0)
        self.profit_loss = 0.0
        self.profit_percentage = 0.0
        
        # Market allocations
        self.allocations = {
            'stocks': 0.0,
            'crypto': 0.0,
            'forex': 0.0
        }
        
        # Performance tracking
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'profit': 0.0
        }
        
        self._init_engines()
    
    def _init_engines(self):
        """Initialize all enabled trading engines"""
        logger.info("🚀 Initializing Multi-Market Engine...")
        
        # Stocks (Alpaca)
        if ALPACA.get('enabled') and TradingEngine:
            try:
                self.stock_engine = TradingEngine(ALPACA)
                logger.info("✅ Stock engine initialized (Alpaca)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize stock engine: {e}")
        
        # Crypto (CCXT)
        if CRYPTO.get('enabled') and CryptoEngine:
            try:
                self.crypto_engine = CryptoEngine(CRYPTO)
                logger.info("✅ Crypto engine initialized (CCXT)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize crypto engine: {e}")
        
        # Forex (OANDA)
        if FOREX.get('enabled') and ForexEngine:
            try:
                self.forex_engine = ForexEngine(FOREX)
                logger.info("✅ Forex engine initialized (OANDA)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize forex engine: {e}")
        
        # Update total capital
        self._update_portfolio_value()
        
        logger.info(f"💰 Total Capital: ${self.total_capital:,.2f}")
    
    def _update_portfolio_value(self):
        """Calculate total capital across all markets"""
        self.total_capital = 0.0
        
        # Stocks
        if self.stock_engine and ALPACA.get('enabled'):
            try:
                stock_value = self.stock_engine.get_portfolio_value()
                self.allocations['stocks'] = stock_value
                self.total_capital += stock_value
            except Exception as e:
                logger.error(f"Error getting stock value: {e}")
        
        # Crypto
        if self.crypto_engine and CRYPTO.get('enabled'):
            try:
                crypto_value = self.crypto_engine.get_portfolio_value()
                self.allocations['crypto'] = crypto_value
                self.total_capital += crypto_value
            except Exception as e:
                logger.error(f"Error getting crypto value: {e}")
        
        # Forex
        if self.forex_engine and FOREX.get('enabled'):
            try:
                forex_balance = self.forex_engine.get_balance()
                forex_value = forex_balance.get('total', 0.0)
                self.allocations['forex'] = forex_value
                self.total_capital += forex_value
            except Exception as e:
                logger.error(f"Error getting forex value: {e}")
        
        # Calculate profit/loss
        self.profit_loss = self.total_capital - self.initial_capital
        if self.initial_capital > 0:
            self.profit_percentage = (self.profit_loss / self.initial_capital) * 100
    
    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary for dashboard"""
        self._update_portfolio_value()
        
        # Get positions from all markets
        positions = []
        
        if self.stock_engine:
            try:
                stock_positions = self.stock_engine.get_positions()
                for pos in stock_positions:
                    positions.append({
                        'symbol': pos.get('symbol', ''),
                        'market': 'stocks',
                        'side': 'LONG' if pos.get('qty', 0) > 0 else 'SHORT',
                        'size': abs(pos.get('qty', 0)),
                        'entry': pos.get('avg_entry_price', 0),
                        'current': pos.get('current_price', 0),
                        'pl': pos.get('unrealized_pl', 0),
                        'pl_percent': pos.get('unrealized_plpc', 0) * 100
                    })
            except Exception as e:
                logger.error(f"Error getting stock positions: {e}")
        
        if self.crypto_engine:
            try:
                crypto_positions = self.crypto_engine.get_positions()
                for pos in crypto_positions:
                    positions.append({
                        'symbol': pos.get('symbol', ''),
                        'market': 'crypto',
                        'side': pos.get('side', 'LONG'),
                        'size': pos.get('size', 0),
                        'entry': pos.get('entry_price', 0),
                        'current': pos.get('current_price', 0),
                        'pl': 0,  # Calculate if needed
                        'pl_percent': 0
                    })
            except Exception as e:
                logger.error(f"Error getting crypto positions: {e}")
        
        if self.forex_engine:
            try:
                forex_positions = self.forex_engine.get_open_positions()
                for pos in forex_positions:
                    positions.append({
                        'symbol': pos.get('instrument', ''),
                        'market': 'forex',
                        'side': 'LONG' if pos.get('net_units', 0) > 0 else 'SHORT',
                        'size': abs(pos.get('net_units', 0)),
                        'entry': 0,
                        'current': 0,
                        'pl': 0,
                        'pl_percent': 0
                    })
            except Exception as e:
                logger.error(f"Error getting forex positions: {e}")
        
        return {
            'total_capital': self.total_capital,
            'initial_capital': self.initial_capital,
            'profit_loss': self.profit_loss,
            'profit_percentage': self.profit_percentage,
            'allocations': self.allocations,
            'positions': positions,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_market_status(self) -> Dict:
        """Get status of all markets"""
        return {
            'stocks': {
                'enabled': ALPACA.get('enabled', False),
                'connected': self.stock_engine is not None and self.stock_engine.is_connected()
            },
            'crypto': {
                'enabled': CRYPTO.get('enabled', False),
                'connected': self.crypto_engine is not None and self.crypto_engine.is_connected()
            },
            'forex': {
                'enabled': FOREX.get('enabled', False),
                'connected': self.forex_engine is not None and self.forex_engine.is_connected()
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def run(self):
        """Main trading loop"""
        self.running = True
        logger.info("🤖 Multi-Market Engine started")
        
        # Start individual engines
        if self.stock_engine:
            self.stock_engine.start()
        if self.crypto_engine:
            # Crypto engine doesn't have start/stop yet
            pass
        if self.forex_engine:
            # Forex engine doesn't have start/stop yet
            pass
        
        while self.running:
            try:
                # Update portfolio value
                self._update_portfolio_value()
                
                # Sleep interval
                time.sleep(AUTO_TRADER.get('scan_interval_seconds', 60))
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
    
    def stop(self):
        """Stop the engine"""
        self.running = False
        logger.info("🛑 Multi-Market Engine stopped")
        
        # Stop individual engines
        if self.stock_engine:
            self.stock_engine.stop()
        
        # Close connections
        if self.forex_engine:
            try:
                self.forex_engine.ctx = None
            except:
                pass


# Singleton instance
_multi_market_engine = None

def get_multi_market_engine() -> MultiMarketEngine:
    """Get or create singleton instance"""
    global _multi_market_engine
    if _multi_market_engine is None:
        _multi_market_engine = MultiMarketEngine()
    return _multi_market_engine