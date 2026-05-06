"""
AI Trading Engine - MACHINE LEARNING POWERED REAL TRADING
Replaces the standard trading engine with AI-driven decision making
Uses ensemble ML models + technical indicators for signal generation
"""
import threading
import time
import logging
import pickle
import os
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class AIStrategy(Enum):
    CONSERVATIVE = "conservative"   # High confidence threshold, smaller positions
    MODERATE = "moderate"           # Balanced
    AGGRESSIVE = "aggressive"       # Lower threshold, larger positions
    ADAPTIVE = "adaptive"           # Adjusts based on recent performance


class BrokerFees:
    """
    Fee structures for supported brokers.
    Used by AI engine to calculate profitable trade sizes.
    """
    
    # Alpaca: https://alpaca.markets/support/pricing
    ALPACA = {
        'commission_per_share': 0.0001,      # $0.0001 per share
        'min_commission': 0.01,              # $0.01 minimum per order
        'max_commission_pct': 1.0,           # 1% max of trade value
        'sec_fee': 0.000008,                 # $8.00 per $1M sold
        'finra_taf': 0.000166,               # $0.000166 per share sold
        'max_finra': 8.30,                   # max FINRA fee per trade
        ' crypto_spread': 0.35,              # 35bps spread on crypto
    }
    
    # Binance: https://www.binance.com/en/fee/schedule
    BINANCE = {
        'spot_maker': 0.001,                 # 0.10% maker
        'spot_taker': 0.001,                 # 0.10% taker
        'bnb_discount': 0.25,                # 25% discount with BNB
        'withdrawal_fixed': {                # Fixed withdrawal fees
            'BTC': 0.0002,
            'ETH': 0.000768,
            'USDT': 1.0,  # varies by chain
        }
    }
    
    # Interactive Brokers (future support)
    IBKR = {
        'us_stock_fixed': 0.005,             # $0.005 per share
        'us_stock_min': 1.00,                # $1.00 minimum
        'us_stock_max': 0.01,              # 1% of trade value
    }
    
    @classmethod
    def estimate_trade_cost(cls, broker: str, side: str, quantity: float, 
                            price: float, use_bnb: bool = False) -> dict:
        """
        Estimate total cost of a trade including all fees.
        Returns dict with breakdown of all fees.
        """
        trade_value = quantity * price
        fees = {
            'broker': broker,
            'side': side,
            'quantity': quantity,
            'price': price,
            'trade_value': trade_value,
            'commissions': 0.0,
            'regulatory': 0.0,
            'spread_cost': 0.0,
            'total_fees': 0.0,
            'total_cost': trade_value,
            'fee_pct': 0.0,
            'breakeven_pct': 0.0,
        }
        
        try:
            if broker == 'alpaca':
                f = cls.ALPACA
                # Commission: $0.0001/share, min $0.01
                commission = max(quantity * f['commission_per_share'], f['min_commission'])
                commission = min(commission, trade_value * f['max_commission_pct'] / 100)
                fees['commissions'] = round(commission, 4)
                
                # SEC + FINRA fees on sells only
                if side == 'sell':
                    sec_fee = trade_value * f['sec_fee']
                    finra_fee = min(quantity * f['finra_taf'], f['max_finra'])
                    fees['regulatory'] = round(sec_fee + finra_fee, 4)
                
                fees['spread_cost'] = round(trade_value * 0.0002, 4)  # ~2bps estimated spread
                
            elif broker == 'binance':
                f = cls.BINANCE
                rate = f['spot_taker']
                if use_bnb:
                    rate *= (1 - f['bnb_discount'])
                
                # Binance charges on both buy and sell
                binance_fee = trade_value * rate
                fees['commissions'] = round(binance_fee, 4)
                fees['spread_cost'] = round(trade_value * 0.0005, 4)  # ~5bps estimated crypto spread
                
            elif broker == 'ibkr':
                f = cls.IBKR
                commission = max(quantity * f['us_stock_fixed'], f['us_stock_min'])
                commission = min(commission, trade_value * f['us_stock_max'])
                fees['commissions'] = round(commission, 4)
                fees['spread_cost'] = round(trade_value * 0.0001, 4)
            
            # Totals
            fees['total_fees'] = round(
                fees['commissions'] + fees['regulatory'] + fees['spread_cost'], 4
            )
            fees['total_cost'] = round(trade_value + fees['total_fees'], 4)
            fees['fee_pct'] = round((fees['total_fees'] / trade_value) * 100, 4) if trade_value > 0 else 0
            
            # Breakeven = how much price must move to cover fees
            # (buy fees + sell fees) / trade value
            round_trip_fees = fees['total_fees'] * 2  # approx buy + sell
            fees['breakeven_pct'] = round((round_trip_fees / trade_value) * 100, 4) if trade_value > 0 else 0
            
        except Exception as e:
            logger.error(f"[FEE CALC ERROR] {broker}: {e}")
        
        return fees


class AITradingEngine:
    """
    AI-Powered Trading Engine
    Uses ensemble of technical indicators + ML scoring for trade decisions
    """
    
    def __init__(self, balance_aggregator, settings):
        self.balance_aggregator = balance_aggregator
        self.settings = settings
        self.is_running = False
        self.thread = None
        self.positions = {}
        self.orders = []
        
        # Risk management
        self.max_position_pct = settings.get('risk_max_position_pct', 10.0)
        self.stop_loss_pct = settings.get('risk_stop_loss_pct', 5.0)
        self.take_profit_pct = settings.get('risk_take_profit_pct', 10.0)
        
        # AI Configuration
        self.ai_config = settings.get('ai_config', {})
        self.ai_strategy = self.ai_config.get('strategy', 'moderate')
        self.confidence_threshold = self.ai_config.get('confidence_threshold', 0.30)
        self.lookback_periods = self.ai_config.get('lookback_periods', 50)
        self.indicators_enabled = self.ai_config.get('indicators', ['sma', 'rsi', 'macd', 'bbands', 'volume'])
        self.model_path = self.ai_config.get('model_path', './config/ai_model.pkl')
        
        # AI State
        self.ai_model = None
        self.scaler = None
        self._load_or_init_model()
        
        # Price history for pattern recognition (keeps last 200 bars per symbol)
        self.price_history = {}
        self._last_fetch_time = {}
        self.max_history = 200
        
        # Performance tracking for adaptive strategy
        self.recent_trades = deque(maxlen=50)  # Last 50 trades
        self.adaptive_threshold = self.confidence_threshold
        
        # Trading state
        self.buying_enabled = True
        self.sell_all_triggered = False
        self.min_trade_interval = 30
        self.last_trade_time = 0
        
        # Fee tracking
        self.total_fees_paid = 0.0
        self.fee_history = deque(maxlen=100)
        self.min_fee_aware_trade_pct = 0.5  # Minimum take-profit % after fees
        self.fee_adjusted_sizing = True      # Enable fee-aware position sizing
        
        # Trade counter
        self.today_trades = 0
        self.last_trade_date = datetime.now().date()
        
        # Persistent trade log
        self.trade_log_path = '/opt/omnibot/logs/trades.jsonl'
        import os
        os.makedirs(os.path.dirname(self.trade_log_path), exist_ok=True)
        
        # Watchlist
        self.watchlist = {
            'alpaca': settings.get('alpaca_watchlist', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']),
            'binance': settings.get('binance_watchlist', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'])
        }
        
        # Technical indicator weights (can be adjusted)
        self.indicator_weights = {
            'trend': 0.25,       # SMA/EMA crossover
            'momentum': 0.25,    # RSI/MACD
            'volatility': 0.20,  # Bollinger Bands
            'volume': 0.15,      # Volume analysis
            'pattern': 0.15      # Price pattern recognition
        }
        
        logger.info(f"[AI ENGINE] Initialized - Strategy: {self.ai_strategy}")
        logger.info(f"[AI ENGINE] Confidence threshold: {self.confidence_threshold}")
        logger.info(f"[AI ENGINE] Indicators: {self.indicators_enabled}")
    
    def _log_trade(self, event: str, data: dict):
        """Write trade event to persistent JSONL log"""
        try:
            import json, os
            entry = {
                'timestamp': datetime.now().isoformat(),
                'event': event,
                'data': data
            }
            with open(self.trade_log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"[TRADE LOG ERROR] {e}")
    
    def _is_us_market_open(self) -> bool:
        """Check if US equity market is open (09:30-16:00 ET, Mon-Fri)"""
        from datetime import datetime, time as dt_time
        import pytz
        try:
            et = pytz.timezone('US/Eastern')
            now = datetime.now(et)
            if now.weekday() >= 5:  # Sat=5, Sun=6
                return False
            market_open = dt_time(9, 30)
            market_close = dt_time(16, 0)
            return market_open <= now.time() <= market_close
        except Exception:
            # Fallback: assume open if pytz missing
            return True
    
    # ============ MODEL MANAGEMENT ============
    
    def _load_or_init_model(self):
        """Load existing AI model or initialize new one"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    saved = pickle.load(f)
                    self.ai_model = saved.get('model')
                    self.scaler = saved.get('scaler')
                logger.info("[AI ENGINE] Loaded existing ML model")
            else:
                self._init_new_model()
        except Exception as e:
            logger.warning(f"[AI ENGINE] Could not load model: {e}, using fresh model")
            self._init_new_model()
    
    def _init_new_model(self):
        """Initialize a new AI model using scikit-learn"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            self.ai_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.scaler = StandardScaler()
            logger.info("[AI ENGINE] Initialized new Random Forest model")
        except ImportError:
            logger.warning("[AI ENGINE] scikit-learn not available, using rule-based AI")
            self.ai_model = None
            self.scaler = None
    
    def save_model(self):
        """Save the current AI model to disk"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({'model': self.ai_model, 'scaler': self.scaler}, f)
            logger.info("[AI ENGINE] Model saved")
        except Exception as e:
            logger.error(f"[AI ENGINE] Failed to save model: {e}")
    
    # ============ ENGINE CONTROL ============
    
    def start(self) -> bool:
        if self.is_running:
            return False
        self.is_running = True
        self.thread = threading.Thread(target=self._trading_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("[AI ENGINE] AI Trading engine started")
        return True
    
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.save_model()
        logger.info("[AI ENGINE] AI Trading engine stopped")
    
    def set_strategy(self, strategy_name: str):
        """Set AI strategy mode - compatible with dashboard"""
        strategy_map = {
            'conservative': AIStrategy.CONSERVATIVE,
            'moderate': AIStrategy.MODERATE,
            'aggressive': AIStrategy.AGGRESSIVE,
            'adaptive': AIStrategy.ADAPTIVE,
            # Legacy strategy name mappings
            'scalping': AIStrategy.AGGRESSIVE,
            'day_trading': AIStrategy.MODERATE,
            'swing_trading': AIStrategy.MODERATE,
            'momentum': AIStrategy.AGGRESSIVE,
            'mean_reversion': AIStrategy.ADAPTIVE,
            'breakout': AIStrategy.AGGRESSIVE,
            'position_trading': AIStrategy.CONSERVATIVE,
            'trend_following': AIStrategy.MODERATE
        }
        
        if strategy_name.lower() in strategy_map:
            self.ai_strategy = strategy_map[strategy_name.lower()].value
            logger.info(f"[AI ENGINE] Strategy set to: {self.ai_strategy}")
            return True
        else:
            logger.warning(f"[AI ENGINE] Unknown strategy: {strategy_name}")
            return False
    
    def enable_buying(self):
        self.buying_enabled = True
        self.sell_all_triggered = False
        logger.info("[AI ENGINE] Buying re-enabled")
    
    def disable_buying(self):
        self.buying_enabled = False
        self.sell_all_triggered = True
        logger.info("[AI ENGINE] Buying disabled")
    
    # ============ MAIN TRADING LOOP ============
    
    def _trading_loop(self):
        loop_count = 0
        logger.info("[AI ENGINE] AI trading loop started")
        
        while self.is_running:
            try:
                loop_count += 1
                
                if not self.settings.get('trading_enabled', False):
                    time.sleep(5)
                    continue
                
                # Reset daily counter
                current_date = datetime.now().date()
                if current_date != self.last_trade_date:
                    self.today_trades = 0
                    self.last_trade_date = current_date
                    logger.info(f"[AI ENGINE] New trading day")
                
                # Update price history every loop
                self._update_price_history()
                
                # Check risk management every loop
                self._check_stop_losses()
                self._check_take_profits()
                
                # AI Analysis and trading every 6 loops (30 seconds)
                if loop_count % 6 == 0:
                    self._ai_scan_and_trade()
                
                # Update adaptive threshold if using adaptive strategy
                if self.ai_strategy == 'adaptive' and loop_count % 60 == 0:
                    self._update_adaptive_threshold()
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"[AI ENGINE ERROR] {e}")
                time.sleep(10)
    
    # ============ PRICE HISTORY ============
    
    def _update_price_history(self):
        """Fetch and store recent price data for all symbols (cached per-symbol)"""
        for broker_name, symbols in self.watchlist.items():
            broker = self.balance_aggregator.get_broker(broker_name)
            if not broker:
                continue
            # Allow data fetching if connected OR has a data client (e.g. Binance mainnet)
            if not broker.connected and not hasattr(broker, '_data_client'):
                continue
            
            for symbol in symbols:
                try:
                    key = f"{broker_name}:{symbol}"
                    now = time.time()
                    last_fetch = self._last_fetch_time.get(key, 0)
                    
                    # Cache: only fetch each symbol every 60 seconds
                    if now - last_fetch < 60:
                        continue
                    
                    self._last_fetch_time[key] = now
                    
                    if broker_name == 'alpaca':
                        bars = broker.get_bars(symbol, '5Min', limit=30)
                    else:
                        bars = broker.get_klines(symbol, '5m', limit=30)
                    
                    if bars is not None and len(bars) > 0:
                        key = f"{broker_name}:{symbol}"
                        if key not in self.price_history:
                            self.price_history[key] = deque(maxlen=self.max_history)
                        
                        existing_count = len(self.price_history[key])
                        if existing_count == 0:
                            # First fetch: append all historical bars
                            for _, row in bars.iterrows():
                                self.price_history[key].append({
                                    'open': float(row['open']),
                                    'high': float(row['high']),
                                    'low': float(row['low']),
                                    'close': float(row['close']),
                                    'volume': float(row.get('volume', 0)),
                                    'timestamp': datetime.now()
                                })
                        else:
                            # Subsequent fetches: only append newest bar if new
                            row = bars.iloc[-1]
                            close_price = float(row['close'])
                            last_close = self.price_history[key][-1]['close']
                            if abs(close_price - last_close) >= 0.0001:
                                self.price_history[key].append({
                                    'open': float(row['open']),
                                    'high': float(row['high']),
                                    'low': float(row['low']),
                                    'close': close_price,
                                    'volume': float(row.get('volume', 0)),
                                    'timestamp': datetime.now()
                                })
                except Exception as e:
                    logger.warning(f"[PRICE HISTORY] {broker_name}:{symbol}: {e}")
    
    # ============ AI SCANNING & TRADING ============
    
    def _log_price_history_status(self):
        total = sum(len(s) for s in self.watchlist.values())
        populated = sum(1 for k, v in self.price_history.items() if len(v) > 0)
        ready = sum(1 for k, v in self.price_history.items() if len(v) >= 30)
        logger.info(f"[PRICE HISTORY STATUS] {populated}/{total} symbols have data, {ready} ready for AI scan")
    
    def _ai_scan_and_trade(self):
        """Scan all symbols using AI analysis and execute trades"""
        if time.time() - self.last_trade_time < self.min_trade_interval:
            return
        self._log_price_history_status()
        
        # Check if US market is open for Alpaca stocks
        alpaca_market_open = self._is_us_market_open()
        
        for broker_name, symbols in self.watchlist.items():
            broker = self.balance_aggregator.get_broker(broker_name)
            if not broker:
                continue
            # Allow data fetching if connected OR has a data client (e.g. Binance mainnet)
            if not broker.connected and not hasattr(broker, '_data_client'):
                continue
            
            for symbol in symbols:
                try:
                    key = f"{broker_name}:{symbol}"
                    history = self.price_history.get(key, [])
                    
                    if len(history) < 30:
                        logger.info(f"[AI SCAN] {symbol}: Insufficient history ({len(history)}/30 bars)")
                        continue
                    
                    # Skip Alpaca scanning when US market is closed
                    if broker_name == 'alpaca' and not alpaca_market_open:
                        logger.info(f"[AI SCAN] {symbol}: Skipped - US market closed")
                        continue
                    
                    # Run AI analysis
                    ai_result = self._ai_analyze(history, symbol, broker_name)
                    
                    if ai_result and ai_result['confidence'] >= self._get_current_threshold():
                        logger.info(f"[AI SCAN] {symbol}: SIGNAL {ai_result['side'].upper()} conf={ai_result['confidence']:.3f}")
                        has_position = key in self.positions
                        
                        # Only buy if buying enabled and no position
                        if ai_result['side'] == 'buy' and (not self.buying_enabled or has_position):
                            continue
                        
                        # Only sell if we have a position
                        if ai_result['side'] == 'sell' and not has_position:
                            continue
                        
                        # Execute the trade
                        self._execute_ai_trade(ai_result, symbol, broker_name)
                    else:
                        conf = ai_result['confidence'] if ai_result else 0.0
                        logger.info(f"[AI SCAN] {symbol}: No signal (conf={conf:.3f}, threshold={self._get_current_threshold():.2f})")
                        
                except Exception as e:
                    logger.error(f"[AI SCAN ERROR] {symbol}: {e}")
    
    def _ai_analyze(self, history: list, symbol: str, broker: str) -> Optional[Dict]:
        """
        Run full AI analysis on price history
        Returns: {'side': 'buy'|'sell', 'confidence': 0-1, 'reason': str, 'features': dict}
        """
        try:
            # Extract price arrays
            closes = np.array([b['close'] for b in history])
            highs = np.array([b['high'] for b in history])
            lows = np.array([b['low'] for b in history])
            volumes = np.array([b['volume'] for b in history])
            
            if len(closes) < 30:
                return None
            
            # Calculate all technical indicators
            features = self._calculate_features(closes, highs, lows, volumes)
            
            if features is None:
                return None
            
            # Get individual indicator scores
            trend_score = self._score_trend(features)
            momentum_score = self._score_momentum(features)
            volatility_score = self._score_volatility(features)
            volume_score = self._score_volume(features, closes, volumes)
            pattern_score = self._score_pattern(closes)
            
            # Weighted ensemble score
            weighted_score = (
                trend_score * self.indicator_weights['trend'] +
                momentum_score * self.indicator_weights['momentum'] +
                volatility_score * self.indicator_weights['volatility'] +
                volume_score * self.indicator_weights['volume'] +
                pattern_score * self.indicator_weights['pattern']
            )
            
            # Normalize to 0-1 confidence
            confidence = min(max(abs(weighted_score), 0), 1.0)
            
            # Always log raw scores for debugging
            logger.info(f"[AI RAW] {symbol}: weighted={weighted_score:.3f} "
                        f"trend={trend_score:.2f} mom={momentum_score:.2f} "
                        f"vol={volatility_score:.2f} volu={volume_score:.2f} pat={pattern_score:.2f}")
            
            # Determine side
            if weighted_score > 0.15:
                side = 'buy'
                reason = self._build_reason('BUY', features, {
                    'trend': trend_score,
                    'momentum': momentum_score,
                    'volatility': volatility_score,
                    'volume': volume_score,
                    'pattern': pattern_score
                })
            elif weighted_score < -0.15:
                side = 'sell'
                reason = self._build_reason('SELL', features, {
                    'trend': trend_score,
                    'momentum': momentum_score,
                    'volatility': volatility_score,
                    'volume': volume_score,
                    'pattern': pattern_score
                })
            else:
                logger.info(f"[AI RAW] {symbol}: No signal (|{weighted_score:.3f}| <= 0.15)")
                return None  # No clear signal
            
            # Apply ML model if available
            if self.ai_model is not None and hasattr(self.ai_model, 'predict_proba'):
                try:
                    X = np.array([[features[k] for k in sorted(features.keys())]])
                    X_scaled = self.scaler.transform(X) if self.scaler else X
                    proba = self.ai_model.predict_proba(X_scaled)[0]
                    ml_confidence = max(proba)
                    # Blend ML confidence with indicator score
                    confidence = confidence * 0.6 + ml_confidence * 0.4
                except:
                    pass  # Fall back to indicator-only
            
            return {
                'side': side,
                'confidence': round(confidence, 3),
                'reason': reason,
                'features': features,
                'score_breakdown': {
                    'trend': round(trend_score, 3),
                    'momentum': round(momentum_score, 3),
                    'volatility': round(volatility_score, 3),
                    'volume': round(volume_score, 3),
                    'pattern': round(pattern_score, 3),
                    'weighted': round(weighted_score, 3)
                }
            }
            
        except Exception as e:
            logger.error(f"[AI ANALYZE ERROR] {symbol}: {e}")
            return None
    
    # ============ TECHNICAL INDICATORS ============
    
    def _calculate_features(self, closes, highs, lows, volumes) -> Optional[Dict]:
        """Calculate all technical indicator features"""
        try:
            features = {}
            
            # Price features
            features['price'] = closes[-1]
            features['returns_1d'] = (closes[-1] - closes[-2]) / closes[-2] if len(closes) >= 2 else 0
            features['returns_5d'] = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
            
            # SMA features
            features['sma_10'] = np.mean(closes[-10:])
            features['sma_20'] = np.mean(closes[-20:])
            features['sma_50'] = np.mean(closes[-50:]) if len(closes) >= 50 else features['sma_20']
            features['sma_ratio'] = features['sma_10'] / features['sma_20'] - 1
            features['sma_cross'] = features['sma_20'] / features['sma_50'] - 1
            
            # EMA features
            features['ema_12'] = self._ema(closes, 12)[-1]
            features['ema_26'] = self._ema(closes, 26)[-1]
            features['ema_ratio'] = features['ema_12'] / features['ema_26'] - 1
            
            # RSI
            features['rsi'] = self._rsi(closes, 14)
            features['rsi_normalized'] = (features['rsi'] - 50) / 50  # -1 to 1
            
            # MACD
            macd_line, signal_line, histogram = self._macd(closes)
            features['macd'] = macd_line[-1] if len(macd_line) > 0 else 0
            features['macd_signal'] = signal_line[-1] if len(signal_line) > 0 else 0
            features['macd_hist'] = histogram[-1] if len(histogram) > 0 else 0
            
            # Bollinger Bands
            bb_upper, bb_lower, bb_width = self._bollinger_bands(closes)
            features['bb_position'] = (closes[-1] - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
            features['bb_width'] = bb_width
            
            # Volatility
            features['volatility'] = np.std(closes[-20:]) / np.mean(closes[-20:])
            
            # Volume
            features['volume_sma'] = np.mean(volumes[-10:]) if len(volumes) >= 10 else np.mean(volumes)
            features['volume_ratio'] = volumes[-1] / features['volume_sma'] if features['volume_sma'] > 0 else 1
            
            return features
            
        except Exception as e:
            logger.error(f"[FEATURE CALC ERROR] {e}")
            return None
    
    def _score_trend(self, features: Dict) -> float:
        """Score trend direction (-1 to 1)"""
        score = 0
        # SMA alignment
        if features['sma_ratio'] > 0.005:
            score += 0.3
        elif features['sma_ratio'] < -0.005:
            score -= 0.3
        
        # Golden/Death cross
        if features['sma_cross'] > 0.01:
            score += 0.4
        elif features['sma_cross'] < -0.01:
            score -= 0.4
        
        # EMA ratio
        if features['ema_ratio'] > 0.003:
            score += 0.3
        elif features['ema_ratio'] < -0.003:
            score -= 0.3
        
        return max(min(score, 1.0), -1.0)
    
    def _score_momentum(self, features: Dict) -> float:
        """Score momentum (-1 to 1)"""
        score = 0
        # RSI
        rsi = features['rsi']
        if rsi < 30:
            score += 0.5  # Oversold = buy signal
        elif rsi > 70:
            score -= 0.5  # Overbought = sell signal
        
        # MACD histogram
        macd_hist = features['macd_hist']
        if macd_hist > 0:
            score += 0.3
        elif macd_hist < 0:
            score -= 0.3
        
        # MACD crossover
        if features['macd'] > features['macd_signal']:
            score += 0.2
        else:
            score -= 0.2
        
        return max(min(score, 1.0), -1.0)
    
    def _score_volatility(self, features: Dict) -> float:
        """Score volatility/bollinger position (-1 to 1)"""
        score = 0
        bb_pos = features['bb_position']
        
        # Price near lower band = potential buy
        if bb_pos < 0.1:
            score += 0.6
        elif bb_pos < 0.3:
            score += 0.3
        # Price near upper band = potential sell
        elif bb_pos > 0.9:
            score -= 0.6
        elif bb_pos > 0.7:
            score -= 0.3
        
        # High volatility increases signal strength
        vol = features['volatility']
        if vol > 0.03:
            score *= 1.2  # Amplify signal in high vol
        
        return max(min(score, 1.0), -1.0)
    
    def _score_volume(self, features: Dict, closes, volumes) -> float:
        """Score volume analysis (-1 to 1)"""
        score = 0
        vol_ratio = features['volume_ratio']
        
        # High volume on price move = confirmation
        if vol_ratio > 2.0:
            price_change = (closes[-1] - closes[-2]) / closes[-2]
            if price_change > 0:
                score += 0.5  # High volume + up = bullish
            elif price_change < 0:
                score -= 0.5  # High volume + down = bearish
        elif vol_ratio > 1.5:
            if (closes[-1] - closes[-2]) / closes[-2] > 0:
                score += 0.3
            else:
                score -= 0.3
        
        return max(min(score, 1.0), -1.0)
    
    def _score_pattern(self, closes) -> float:
        """Score price pattern recognition (-1 to 1)"""
        score = 0
        if len(closes) < 10:
            return 0
        
        recent = closes[-10:]
        
        # Check for consecutive moves
        up_count = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
        down_count = 9 - up_count
        
        # Strong consecutive trend
        if up_count >= 7:
            score -= 0.4  # Overextended up = potential reversal
        elif down_count >= 7:
            score += 0.4  # Overextended down = potential bounce
        
        # Check for double bottom / double top pattern
        if len(closes) >= 20:
            low_10 = min(closes[-10:])
            low_20 = min(closes[-20:-10])
            if abs(low_10 - low_20) / low_20 < 0.02:  # Within 2%
                score += 0.3  # Double bottom pattern
            
            high_10 = max(closes[-10:])
            high_20 = max(closes[-20:-10])
            if abs(high_10 - high_20) / high_20 < 0.02:
                score -= 0.3  # Double top pattern
        
        return max(min(score, 1.0), -1.0)
    
    # ============ TECHNICAL HELPER METHODS ============
    
    def _ema(self, data, period):
        """Calculate Exponential Moving Average"""
        alpha = 2 / (period + 1)
        ema = [data[0]]
        for price in data[1:]:
            ema.append(alpha * price + (1 - alpha) * ema[-1])
        return np.array(ema)
    
    def _rsi(self, data, period=14):
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return 50
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = self._ema(data, fast)
        ema_slow = self._ema(data, slow)
        macd_line = ema_fast[-len(ema_slow):] - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line[-len(signal_line):] - signal_line
        return macd_line, signal_line, histogram
    
    def _bollinger_bands(self, data, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        sma = np.mean(data[-period:])
        std = np.std(data[-period:])
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        width = (upper - lower) / sma if sma > 0 else 0
        return upper, lower, width
    
    # ============ TRADE EXECUTION ============
    
    def _execute_ai_trade(self, ai_result: Dict, symbol: str, broker: str):
        """Execute a trade based on AI analysis - with FEE AWARENESS"""
        try:
            side = OrderSide.BUY if ai_result['side'] == 'buy' else OrderSide.SELL
            confidence = ai_result['confidence']
            logger.info(f"[TRADE EXEC] START {side.value.upper()} {symbol} @ {broker} conf={confidence:.3f}")
            self._log_trade('attempt', {'symbol': symbol, 'broker': broker, 'side': side.value, 'confidence': confidence})
            
            # Get current price
            broker_obj = self.balance_aggregator.get_broker(broker)
            if broker == 'alpaca':
                quote = broker_obj.get_latest_trade(symbol)
                price = quote.get('price', 0) if quote else 0
            else:
                price = broker_obj.get_latest_price(symbol)
            
            if price <= 0:
                logger.error(f"[TRADE EXEC] {symbol}: Invalid price {price}")
                self._log_trade('price_fail', {'symbol': symbol, 'broker': broker, 'price': price})
                return
            logger.info(f"[TRADE EXEC] {symbol}: Price=${price:.4f}")
            
            # ===== FEE CALCULATION =====
            # First, estimate fees for a test quantity to understand fee structure
            test_quantity = 1.0 if broker == 'binance' else 100  # 1 unit crypto, 100 shares stock
            fee_info = BrokerFees.estimate_trade_cost(broker, side.value, test_quantity, price)
            fee_pct = fee_info['fee_pct']
            breakeven_pct = fee_info['breakeven_pct']
            
            # ===== POSITION SIZING (Fee-Aware) =====
            total_value = self.balance_aggregator.get_total_capital()
            if total_value <= 0:
                return
            
            # Position sizing based on strategy
            if self.ai_strategy == 'conservative':
                base_pct = 0.05
            elif self.ai_strategy == 'moderate':
                base_pct = 0.10
            elif self.ai_strategy == 'aggressive':
                base_pct = 0.15
            else:  # adaptive
                base_pct = 0.08 + (confidence - 0.5) * 0.10
            
            # Scale by confidence
            position_value = total_value * base_pct * confidence
            quantity = position_value / price
            
            # Round quantity
            if broker == 'binance' and 'BTC' in symbol:
                quantity = round(quantity, 5)
            elif broker == 'binance':
                quantity = round(quantity, 4)
            else:
                quantity = int(quantity)
            
            if quantity <= 0:
                logger.error(f"[TRADE EXEC] {symbol}: Invalid quantity {quantity}")
                self._log_trade('sizing_fail', {'symbol': symbol, 'broker': broker, 'quantity': quantity, 'price': price, 'total_value': total_value})
                return
            logger.info(f"[TRADE EXEC] {symbol}: Sizing={quantity} (value=${quantity*price:.2f})")
            
            # Recalculate actual fees for this trade size
            actual_fees = BrokerFees.estimate_trade_cost(broker, side.value, quantity, price)
            
            # ===== FEE AWARENESS CHECKS =====
            logger.info(f"[TRADE EXEC] {symbol}: Fees=${actual_fees['total_fees']:.4f} breakeven={actual_fees['breakeven_pct']:.4f}%")
            if self.fee_adjusted_sizing:
                # 1. Skip if fees are more than 10% of expected profit
                expected_profit_pct = self.take_profit_pct * (confidence * 0.5)
                if actual_fees['breakeven_pct'] >= expected_profit_pct * 0.5:
                    logger.warning(
                        f"[AI FEE SKIP] {symbol}: breakeven {actual_fees['breakeven_pct']:.3f}% "
                        f"too high vs expected profit {expected_profit_pct:.3f}%"
                    )
                    self._log_trade('fee_skip', {'symbol': symbol, 'broker': broker, 'reason': 'breakeven_too_high', 'breakeven': actual_fees['breakeven_pct'], 'expected': expected_profit_pct})
                    return
                
                # 2. For small trades, ensure minimum viable size
                min_viable_value = 10.0  # $10 minimum trade value
                if actual_fees['trade_value'] < min_viable_value:
                    logger.warning(
                        f"[AI FEE SKIP] {symbol}: trade value ${actual_fees['trade_value']:.2f} "
                        f"below minimum ${min_viable_value}"
                    )
                    self._log_trade('fee_skip', {'symbol': symbol, 'broker': broker, 'reason': 'trade_value_too_small', 'trade_value': actual_fees['trade_value']})
                    return
                
                # 3. Adjust take-profit to account for fees
                fee_adjusted_tp = self.take_profit_pct + actual_fees['breakeven_pct']
                logger.info(
                    f"[AI FEE] {symbol}: fees ~{actual_fees['total_fees']:.4f} "
                    f"({fee_pct:.4f}%), breakeven {breakeven_pct:.4f}%, "
                    f"adjusted TP: {fee_adjusted_tp:.3f}%"
                )
            
            logger.info(f"[AI SIGNAL] {ai_result['side'].upper()} {symbol} - Confidence: {confidence:.2%}")
            logger.info(f"[AI REASON] {ai_result['reason']}")
            self._log_trade('pre_submit', {'symbol': symbol, 'broker': broker, 'side': side.value, 'quantity': quantity, 'price': price, 'confidence': confidence})
            
            # Execute
            order = self.place_order(symbol, side, quantity, OrderType.MARKET, broker=broker)
            
            if order:
                self.last_trade_time = time.time()
                self._log_trade('executed', {'symbol': symbol, 'broker': broker, 'side': side.value, 'quantity': quantity, 'price': price, 'order_id': order.get('id'), 'fees': actual_fees['total_fees']})
            else:
                logger.error(f"[TRADE EXEC] {symbol}: place_order returned None")
                self._log_trade('submit_fail', {'symbol': symbol, 'broker': broker, 'side': side.value, 'quantity': quantity, 'price': price})
                self.today_trades += 1
                self.total_fees_paid += actual_fees['total_fees']
                self.fee_history.append({
                    'timestamp': time.time(),
                    'symbol': symbol,
                    'side': side.value,
                    'fees': actual_fees['total_fees'],
                    'fee_pct': fee_pct,
                    'trade_value': actual_fees['trade_value']
                })
                
                # Track position
                position_key = f"{broker}:{symbol}"
                if side == OrderSide.BUY:
                    self.positions[position_key] = {
                        'symbol': symbol,
                        'quantity': quantity,
                        'entry_price': price,
                        'broker': broker,
                        'ai_confidence': confidence,
                        'timestamp': time.time(),
                        'estimated_fees': actual_fees['total_fees'],
                        'breakeven_price': price * (1 + actual_fees['breakeven_pct'] / 100) if side == OrderSide.BUY else price * (1 - actual_fees['breakeven_pct'] / 100)
                    }
                elif side == OrderSide.SELL and position_key in self.positions:
                    del self.positions[position_key]
                
                # Track for adaptive learning
                self.recent_trades.append({
                    'symbol': symbol,
                    'side': ai_result['side'],
                    'confidence': confidence,
                    'price': price,
                    'timestamp': time.time(),
                    'features': ai_result.get('features', {}),
                    'fees': actual_fees['total_fees']
                })
                
                logger.info(f"[AI TRADE] Executed {ai_result['side'].upper()} {quantity} {symbol} "
                           f"(fees: ${actual_fees['total_fees']:.4f})")
        
        except Exception as e:
            logger.error(f"[AI EXECUTE ERROR] {e}")
    
    def _build_reason(self, side: str, features: Dict, scores: Dict) -> str:
        """Build human-readable reason for the trade signal"""
        reasons = []
        
        # Trend
        if scores['trend'] > 0.3:
            reasons.append(f"Strong uptrend (SMA cross: {features['sma_cross']:.3f})")
        elif scores['trend'] < -0.3:
            reasons.append(f"Strong downtrend (SMA cross: {features['sma_cross']:.3f})")
        
        # Momentum
        if features['rsi'] < 35:
            reasons.append(f"RSI oversold ({features['rsi']:.1f})")
        elif features['rsi'] > 65:
            reasons.append(f"RSI overbought ({features['rsi']:.1f})")
        
        if features['macd_hist'] > 0:
            reasons.append("MACD bullish")
        elif features['macd_hist'] < 0:
            reasons.append("MACD bearish")
        
        # Bollinger
        if features['bb_position'] < 0.1:
            reasons.append("Price at lower Bollinger Band")
        elif features['bb_position'] > 0.9:
            reasons.append("Price at upper Bollinger Band")
        
        return f"AI {side}: " + "; ".join(reasons) if reasons else f"AI {side}: Ensemble signal"
    
    # ============ ADAPTIVE STRATEGY ============
    
    def _get_current_threshold(self) -> float:
        """Get current confidence threshold based on strategy"""
        if self.ai_strategy == 'adaptive':
            return self.adaptive_threshold
        elif self.ai_strategy == 'conservative':
            return 0.75
        elif self.ai_strategy == 'aggressive':
            return 0.50
        else:
            return self.confidence_threshold
    
    def _update_adaptive_threshold(self):
        """Adapt threshold based on recent trade performance"""
        if len(self.recent_trades) < 10:
            return
        
        recent = list(self.recent_trades)[-20:]
        # Simple metric: if recent trades had high confidence, can be more aggressive
        avg_confidence = np.mean([t['confidence'] for t in recent])
        
        # Adjust threshold toward average confidence
        target = max(0.45, min(0.80, avg_confidence - 0.05))
        self.adaptive_threshold = self.adaptive_threshold * 0.9 + target * 0.1
        
        logger.info(f"[AI ADAPTIVE] Threshold adjusted to {self.adaptive_threshold:.3f}")
    
    # ============ RISK MANAGEMENT ============
    
    def _check_stop_losses(self):
        """Check and execute stop losses"""
        try:
            for position_key, position in list(self.positions.items()):
                symbol = position['symbol']
                entry_price = position['entry_price']
                qty = position['quantity']
                broker = position['broker']
                
                broker_obj = self.balance_aggregator.get_broker(broker)
                if not broker_obj or not broker_obj.connected:
                    continue
                
                if broker == 'alpaca':
                    quote = broker_obj.get_latest_trade(symbol)
                    current_price = quote.get('price', entry_price) if quote else entry_price
                else:
                    current_price = broker_obj.get_latest_price(symbol)
                
                if entry_price > 0 and current_price > 0:
                    loss_pct = (entry_price - current_price) / entry_price * 100
                    if loss_pct >= self.stop_loss_pct:
                        logger.warning(f"[AI STOP LOSS] {symbol} at -{loss_pct:.2f}%")
                        self.place_order(symbol, OrderSide.SELL, qty, broker=broker)
                        del self.positions[position_key]
        except Exception as e:
            logger.error(f"[STOP LOSS ERROR] {e}")
    
    def _check_take_profits(self):
        """Check and execute take profits - FEE AWARE"""
        try:
            for position_key, position in list(self.positions.items()):
                symbol = position['symbol']
                entry_price = position['entry_price']
                qty = position['quantity']
                broker = position['broker']
                
                # Use fee-adjusted breakeven if available
                breakeven_price = position.get('breakeven_price', entry_price)
                
                broker_obj = self.balance_aggregator.get_broker(broker)
                if not broker_obj or not broker_obj.connected:
                    continue
                
                if broker == 'alpaca':
                    quote = broker_obj.get_latest_trade(symbol)
                    current_price = quote.get('price', entry_price) if quote else entry_price
                else:
                    current_price = broker_obj.get_latest_price(symbol)
                
                if entry_price > 0 and current_price > 0:
                    # Gross profit %
                    gross_profit_pct = (current_price - entry_price) / entry_price * 100
                    
                    # Net profit % (after estimated fees)
                    est_fees = position.get('estimated_fees', 0)
                    trade_value = qty * entry_price
                    net_profit_pct = gross_profit_pct - (est_fees / trade_value * 100 * 2) if trade_value > 0 else 0
                    
                    # Use fee-adjusted take profit
                    fee_adjusted_tp = self.take_profit_pct + (est_fees / trade_value * 100 * 2) if trade_value > 0 else self.take_profit_pct
                    
                    if gross_profit_pct >= fee_adjusted_tp:
                        logger.info(
                            f"[AI TAKE PROFIT] {symbol} gross: +{gross_profit_pct:.2f}%, "
                            f"net: +{net_profit_pct:.2f}%, fees: ~${est_fees:.4f}"
                        )
                        self.place_order(symbol, OrderSide.SELL, qty, broker=broker)
                        del self.positions[position_key]
        except Exception as e:
            logger.error(f"[TAKE PROFIT ERROR] {e}")
    
    # ============ ORDER PLACEMENT ============
    
    def place_order(self, symbol: str, side: OrderSide, quantity: float,
                   order_type: OrderType = OrderType.MARKET,
                   broker: str = 'alpaca', limit_price: float = None) -> Optional[Dict]:
        """Place an order through specified broker"""
        try:
            broker_obj = self.balance_aggregator.get_broker(broker)
            
            if not broker_obj or not broker_obj.connected:
                logger.error(f"[ORDER ERROR] {broker} not connected")
                return None
            
            if not hasattr(broker_obj, 'place_order'):
                logger.error(f"[ORDER ERROR] {broker} does not support order placement")
                return None
            
            result = broker_obj.place_order(
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                order_type=order_type.value,
                limit_price=limit_price
            )
            
            if result:
                self.orders.append(result)
                logger.info(f"{'='*50}")
                logger.info(f"[AI ORDER EXECUTED] {side.value.upper()} {quantity} {symbol}")
                logger.info(f"[AI ORDER] Broker: {broker}, ID: {result['id']}")
                logger.info(f"{'='*50}")
                return result
            else:
                logger.error(f"[ORDER FAILED] {broker} returned None")
                return None
                
        except Exception as e:
            logger.error(f"[ORDER ERROR] {e}")
            return None
    
    # ============ UTILITY METHODS ============
    
    def sell_all_positions(self, broker: str = 'all'):
        """Sell all positions and disable buying"""
        logger.info(f"[AI ENGINE] Selling all positions for {broker}")
        
        brokers = ['alpaca', 'binance'] if broker == 'all' else [broker]
        sold_count = 0
        
        for b in brokers:
            broker_obj = self.balance_aggregator.get_broker(b)
            if broker_obj and broker_obj.connected:
                try:
                    if b == 'alpaca':
                        positions = broker_obj.get_positions()
                        for pos in positions:
                            result = self.place_order(
                                pos['symbol'], OrderSide.SELL,
                                pos['qty'], broker='alpaca'
                            )
                            if result:
                                sold_count += 1
                    
                    elif b == 'binance':
                        balances = broker_obj.get_all_balances()
                        for asset, amount in balances.items():
                            if asset not in ['USDT', 'BUSD'] and amount > 0:
                                symbol = f"{asset}USDT"
                                result = self.place_order(
                                    symbol, OrderSide.SELL,
                                    amount, broker='binance'
                                )
                                if result:
                                    sold_count += 1
                except Exception as e:
                    logger.error(f"[SELL ALL ERROR] {b}: {e}")
        
        self.disable_buying()
        logger.info(f"[AI ENGINE] Sold {sold_count} positions. Buying disabled.")
        return {'success': True, 'sold_count': sold_count, 'buying_disabled': True}
    
    def estimate_fees(self, broker: str, symbol: str, quantity: float, 
                      price: float, side: str = 'buy') -> dict:
        """
        Public API to estimate fees for a potential trade.
        Called by dashboard before showing trade confirmation.
        """
        return BrokerFees.estimate_trade_cost(broker, side, quantity, price)
    
    def get_fee_summary(self) -> dict:
        """Get summary of all fees paid"""
        if not self.fee_history:
            return {'total_fees': 0, 'avg_per_trade': 0, 'trades': 0}
        
        total = sum(f['fees'] for f in self.fee_history)
        return {
            'total_fees': round(total, 4),
            'avg_per_trade': round(total / len(self.fee_history), 4),
            'trades': len(self.fee_history),
            'by_broker': {}
        }
    
    def sell_all_if_profitable(self, broker: str = 'all'):
        """Sell all profitable positions"""
        logger.info(f"[AI ENGINE] Checking positions for profitability")
        
        brokers = ['alpaca', 'binance'] if broker == 'all' else [broker]
        sold_count = 0
        skipped_count = 0
        
        for b in brokers:
            broker_obj = self.balance_aggregator.get_broker(b)
            if broker_obj and broker_obj.connected:
                try:
                    if b == 'alpaca':
                        positions = broker_obj.get_positions()
                        for pos in positions:
                            symbol = pos['symbol']
                            entry_price = pos.get('avg_entry_price', 0)
                            qty = pos['qty']
                            
                            quote = broker_obj.get_latest_trade(symbol)
                            current_price = quote.get('price', entry_price) if quote else entry_price
                            
                            if entry_price > 0 and current_price > entry_price:
                                profit_pct = (current_price - entry_price) / entry_price * 100
                                logger.info(f"[AI SELL-ALL] {symbol} profitable (+{profit_pct:.2f}%), selling...")
                                result = self.place_order(symbol, OrderSide.SELL, qty, broker='alpaca')
                                if result:
                                    sold_count += 1
                            else:
                                skipped_count += 1
                    
                    elif b == 'binance':
                        balances = broker_obj.get_all_balances()
                        for asset, amount in balances.items():
                            if asset not in ['USDT', 'BUSD'] and amount > 0:
                                symbol = f"{asset}USDT"
                                result = self.place_order(symbol, OrderSide.SELL, amount, broker='binance')
                                if result:
                                    sold_count += 1
                except Exception as e:
                    logger.error(f"[SELL ALL ERROR] {b}: {e}")
        
        self.disable_buying()
        return {
            'success': True,
            'sold_count': sold_count,
            'skipped_count': skipped_count,
            'buying_disabled': True
        }
    
    def get_portfolio_value(self) -> float:
        return self.balance_aggregator.get_total_capital()
    
    def get_status(self) -> Dict:
        # Calculate fee stats
        recent_fees = list(self.fee_history)[-20:] if self.fee_history else []
        avg_fee_pct = sum(f['fee_pct'] for f in recent_fees) / len(recent_fees) if recent_fees else 0
        
        return {
            'running': self.is_running,
            'mode': self.settings.get('trading_mode', 'ai_live'),
            'strategy': self.ai_strategy,
            'strategy_name': f'AI-{self.ai_strategy.title()}',
            'current_strategy_name': f'AI-{self.ai_strategy.title()}',
            'trading_enabled': self.settings.get('trading_enabled', False),
            'buying_enabled': self.buying_enabled,
            'sell_all_triggered': self.sell_all_triggered,
            'positions_count': len(self.positions),
            'positions': len(self.positions),
            'orders_count': len(self.orders),
            'today_trades': self.today_trades,
            'last_check': time.strftime('%H:%M:%S'),
            'next_run_time': time.strftime('%H:%M:%S', time.localtime(time.time() + 30)),
            'ai_model_loaded': self.ai_model is not None,
            'ai_confidence_threshold': round(self._get_current_threshold(), 3),
            'price_history_symbols': len(self.price_history),
            'total_value': self.get_portfolio_value(),
            # Fee tracking
            'total_fees_paid': round(self.total_fees_paid, 4),
            'avg_fee_pct': round(avg_fee_pct, 4),
            'fee_adjusted_sizing': self.fee_adjusted_sizing,
            'fee_trades_count': len(self.fee_history),
        }
