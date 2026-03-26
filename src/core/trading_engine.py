"""
OMNIBOT v2.7 Titan - Stock Trading Engine (Alpaca)
Handles stock trading with 5 modes: Conservative, Moderate, Aggressive, HFT, Sentinel
"""

import random
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

try:
    import alpaca_trade_api as tradeapi
except ImportError:
    tradeapi = None

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    HFT = "hft"
    SENTINEL = "sentinel"


class TradingEngine:
    """Stock trading engine using Alpaca API"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.api = None
        self.mode = TradingMode.MODERATE
        self.is_running = False
        self.positions = []
        self.trade_history = []
        
        # Strategy stats
        self.strategy_stats = {
            'momentum': {'trades': 0, 'wins': 0, 'profit': 0},
            'mean_reversion': {'trades': 0, 'wins': 0, 'profit': 0},
            'breakout': {'trades': 0, 'wins': 0, 'profit': 0},
            'ml_ensemble': {'trades': 0, 'wins': 0, 'profit': 0}
        }
        
        self.last_trade_time = {}
        self.daily_pnl = 0
        self.daily_trades = 0
        
        if self.enabled and tradeapi:
            self._connect()
    
    def _connect(self):
        """Connect to Alpaca API"""
        try:
            self.api = tradeapi.REST(
                self.config['api_key'],
                self.config['secret_key'],
                self.config['base_url']
            )
            account = self.api.get_account()
            logger.info(f"✅ Alpaca connected (Paper: {self.config.get('paper', True)})")
            logger.info(f"   Balance: ${float(account.portfolio_value):,.2f}")
        except Exception as e:
            logger.error(f"❌ Alpaca connection failed: {e}")
            self.enabled = False
    
    def is_connected(self) -> bool:
        """Check if connected to Alpaca"""
        return self.api is not None and self.enabled
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        if not self.is_connected():
            return 0.0
        try:
            account = self.api.get_account()
            return float(account.portfolio_value)
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 0.0
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.is_connected():
            return []
        try:
            positions = self.api.list_positions()
            return [{
                'symbol': p.symbol,
                'qty': int(p.qty),
                'avg_entry_price': float(p.avg_entry_price),
                'current_price': float(p.current_price),
                'unrealized_pl': float(p.unrealized_pl),
                'unrealized_plpc': float(p.unrealized_plpc)
            } for p in positions]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def place_order(self, symbol: str, qty: int, side: str) -> Dict:
        """Place a stock order"""
        if not self.is_connected():
            return {'status': 'error', 'message': 'Not connected'}
        
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='day'
            )
            logger.info(f"✅ Order placed: {side} {qty} {symbol}")
            return {
                'status': order.status,
                'id': order.id,
                'symbol': symbol,
                'qty': qty,
                'side': side
            }
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def set_mode(self, mode: TradingMode):
        """Set trading mode"""
        self.mode = mode
        logger.info(f"🎮 Mode changed to: {mode.value.upper()}")
    
    def start(self):
        """Start trading engine"""
        self.is_running = True
        logger.info(f"🚀 Trading engine started in {self.mode.value.upper()} mode")
        
        if self.mode == TradingMode.HFT:
            threading.Thread(target=self._hft_loop, daemon=True).start()
        else:
            threading.Thread(target=self._trading_loop, daemon=True).start()
    
    def stop(self):
        """Stop trading engine"""
        self.is_running = False
        logger.info("🛑 Trading engine stopped")
    
    def _trading_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                if self.mode != TradingMode.SENTINEL:
                    self._evaluate_strategies()
                
                # Sleep based on mode
                sleep_times = {
                    TradingMode.CONSERVATIVE: 300,
                    TradingMode.MODERATE: 120,
                    TradingMode.AGGRESSIVE: 60,
                    TradingMode.HFT: 30
                }
                time.sleep(sleep_times.get(self.mode, 120))
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(60)
    
    def _hft_loop(self):
        """High frequency trading loop"""
        logger.info("⚡ HFT mode active - scanning every 30 seconds")
        while self.is_running and self.mode == TradingMode.HFT:
            try:
                self._evaluate_strategies()
                time.sleep(30)
            except Exception as e:
                logger.error(f"HFT error: {e}")
                time.sleep(10)
    
    def _evaluate_strategies(self):
        """Evaluate all trading strategies"""
        strategies = ['momentum', 'mean_reversion', 'breakout', 'ml_ensemble']
        
        for strategy in strategies:
            # Check cooldown
            last_trade = self.last_trade_time.get(strategy, 0)
            cooldown = 60 if self.mode == TradingMode.HFT else 300
            
            if time.time() - last_trade < cooldown:
                continue
            
            signal = self._generate_signal(strategy)
            if signal:
                self._execute_trade(strategy, signal)
    
    def _generate_signal(self, strategy: str) -> Optional[Dict]:
        """Generate trading signal for a strategy"""
        # Base confidence levels
        base_confidence = {
            'momentum': 0.65,
            'mean_reversion': 0.60,
            'breakout': 0.62,
            'ml_ensemble': 0.70
        }
        
        confidence = base_confidence.get(strategy, 0.60)
        confidence += (random.random() - 0.5) * 0.2  # Add noise
        
        # Mode-specific thresholds
        thresholds = {
            TradingMode.CONSERVATIVE: 0.75,
            TradingMode.MODERATE: 0.65,
            TradingMode.AGGRESSIVE: 0.55,
            TradingMode.HFT: 0.48
        }
        
        threshold = thresholds.get(self.mode, 0.65)
        
        if confidence >= threshold:
            return {
                'strategy': strategy,
                'confidence': confidence,
                'direction': 'buy' if random.random() > 0.5 else 'sell'
            }
        
        return None
    
    def _execute_trade(self, strategy: str, signal: Dict):
        """Execute a trade based on signal"""
        # This is a placeholder - implement actual trading logic
        self.last_trade_time[strategy] = time.time()
        self.strategy_stats[strategy]['trades'] += 1
        logger.info(f"📊 Trade signal: {signal['direction'].upper()} via {strategy}")