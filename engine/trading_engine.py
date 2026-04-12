"""
Trading Engine
Core trading logic and order execution
"""

import threading
import time
import logging
import random
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class TradingStrategy(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class Signal:
    """Trading signal"""
    def __init__(self, symbol: str, side: OrderSide, confidence: float, 
                 reason: str, broker: str = 'alpaca'):
        self.symbol = symbol
        self.side = side
        self.confidence = confidence
        self.reason = reason
        self.broker = broker
        self.timestamp = time.time()


class TradingEngine:
    """Main trading engine with risk management and automated strategies"""
    
    def __init__(self, balance_aggregator, settings):
        self.balance_aggregator = balance_aggregator
        self.settings = settings
        self.is_running = False
        self.thread = None
        self.positions = {}
        self.orders = []
        
        # Risk management settings
        self.max_position_pct = 10.0  # Max 10% per position
        self.stop_loss_pct = 5.0      # 5% stop loss
        self.take_profit_pct = 10.0   # 10% take profit
        
        # Trading parameters
        self.last_trade_time = 0
        self.min_trade_interval = 10  # Minimum seconds between trades (was 60)
        self.daily_trade_limit = 999999  # Unlimited trades (was 50, then 10)
        self.today_trades = 0
        self.last_trade_date = datetime.now().date()
        
        # Check for high-frequency mode in settings
        self.high_frequency = settings.get('high_frequency', False)
        if self.high_frequency:
            self.min_trade_interval = 5  # 5 seconds between trades
            self.daily_trade_limit = 999999  # Unlimited trades in high-frequency mode
            logger.info("[ENGINE] High-frequency mode enabled")
        
        # Expanded watchlist for trading - 35 stocks, 25 cryptos
        self.watchlist = {
            'alpaca': [
                # Tech Giants
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
                # Semiconductors
                'AMD', 'INTC', 'AVGO', 'QCOM', 'TXN', 'MU', 'AMAT',
                # Software/SaaS
                'CRM', 'ADBE', 'ORCL', 'INTU', 'NOW', 'SNOW', 'ZM',
                # Finance
                'JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK',
                # Consumer
                'DIS', 'NKE', 'HD', 'LOW', 'COST', 'MCD', 'SBUX', 'TGT',
                # Healthcare
                'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY',
                # ETFs
                'SPY', 'QQQ', 'IWM', 'VIXY'
            ],
            'binance': [
                # Major Caps
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
                # Mid Caps
                'DOTUSDT', 'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'LTCUSDT',
                'BCHUSDT', 'FILUSDT', 'ETCUSDT', 'XLMUSDT', 'VETUSDT',
                # DeFi
                'AAVEUSDT', 'SUSHIUSDT', 'COMPUSDT', 'MKRUSDT', 'CRVUSDT',
                # Layer 1s
                'ATOMUSDT', 'NEARUSDT', 'ALGOUSDT', 'FTMUSDT', 'AVAXUSDT',
                # Meme/Other
                'DOGEUSDT', 'SHIBUSDT', 'TRXUSDT', 'EOSUSDT', 'XMRUSDT'
            ]
        }
        
        # Price history for momentum calculation (mock data)
        self.price_history = {}
        self.signals_generated = []
        
    def start(self) -> bool:
        """Start the trading engine"""
        if self.is_running:
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._trading_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"[ENGINE] Trading engine started")
        logger.info(f"[ENGINE] Watchlist: {len(self.watchlist['alpaca'])} stocks, {len(self.watchlist['binance'])} cryptos")
        return True
    
    def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[ENGINE] Trading engine stopped")
    
    def _trading_loop(self):
        """Main trading loop"""
        loop_count = 0
        while self.is_running:
            try:
                loop_count += 1
                
                # Only trade if enabled
                if not self.settings.get('trading_enabled', False):
                    time.sleep(5)
                    continue
                
                # Reset daily trade count
                current_date = datetime.now().date()
                if current_date != self.last_trade_date:
                    self.today_trades = 0
                    self.last_trade_date = current_date
                
                # Check positions and manage risk
                self._check_stop_losses()
                self._check_take_profits()
                
                # Evaluate strategies and trade
                # High-frequency: scan every loop (5 seconds), Normal: every 12 loops (60 seconds)
                scan_interval = 1 if self.high_frequency else 12
                if loop_count % scan_interval == 0:
                    self._scan_for_opportunities()
                
                # Process any pending signals
                self._process_signals()
                
                time.sleep(5)  # 5 second loop
                
            except Exception as e:
                logger.error(f"[ENGINE ERROR] {e}")
                time.sleep(10)
    
    def _scan_for_opportunities(self):
        """Scan watchlist for trading opportunities"""
        strategy = self.settings.get('strategy', 'moderate')
        
        # Check if we can trade today
        if self.today_trades >= self.daily_trade_limit:
            return
        
        # Check minimum interval between trades
        if time.time() - self.last_trade_time < self.min_trade_interval:
            return
        
        # Scan stocks (Alpaca)
        broker = self.balance_aggregator.get_broker('alpaca')
        if broker and broker.connected:
            for symbol in self.watchlist['alpaca']:
                signal = self._generate_signal(symbol, 'alpaca', strategy)
                if signal and signal.confidence > 0.6:
                    self.signals_generated.append(signal)
                    logger.info(f"[SIGNAL] {signal.side.value.upper()} {symbol} ({signal.broker}) - {signal.reason}")
        
        # Scan crypto (Binance)  
        broker = self.balance_aggregator.get_broker('binance')
        if broker and broker.connected:
            for symbol in self.watchlist['binance']:
                signal = self._generate_signal(symbol, 'binance', strategy)
                if signal and signal.confidence > 0.6:
                    self.signals_generated.append(signal)
                    logger.info(f"[SIGNAL] {signal.side.value.upper()} {symbol} ({signal.broker}) - {signal.reason}")
    
    def _generate_signal(self, symbol: str, broker: str, strategy: str) -> Optional[Signal]:
        """Generate trading signal for a symbol"""
        try:
            # Get or create price history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            # Simulate price fetching (in real implementation, fetch from broker API)
            current_price = self._get_mock_price(symbol)
            self.price_history[symbol].append(current_price)
            
            # Keep only last 20 prices
            if len(self.price_history[symbol]) > 20:
                self.price_history[symbol] = self.price_history[symbol][-20:]
            
            # Need at least 10 prices for analysis
            if len(self.price_history[symbol]) < 10:
                return None
            
            prices = self.price_history[symbol]
            
            # Calculate moving averages
            sma_short = sum(prices[-5:]) / 5   # 5-period SMA
            sma_long = sum(prices[-10:]) / 10  # 10-period SMA
            
            # Calculate momentum (price change %)
            momentum = ((prices[-1] - prices[-5]) / prices[-5]) * 100
            
            # Check current position
            current_position = self._get_position(symbol, broker)
            
            # Generate signals based on strategy and momentum
            if strategy == 'conservative':
                # Only trade on strong trends
                if sma_short > sma_long * 1.02 and momentum > 2 and not current_position:
                    return Signal(symbol, OrderSide.BUY, 0.8, f"Strong uptrend (momentum: +{momentum:.1f}%)", broker)
                elif sma_short < sma_long * 0.98 and current_position:
                    return Signal(symbol, OrderSide.SELL, 0.8, f"Trend reversal (momentum: {momentum:.1f}%)", broker)
                    
            elif strategy == 'moderate':
                # Trade on moderate trends
                if sma_short > sma_long * 1.01 and momentum > 1 and not current_position:
                    return Signal(symbol, OrderSide.BUY, 0.7, f"Uptrend detected (momentum: +{momentum:.1f}%)", broker)
                elif sma_short < sma_long * 0.99 and current_position:
                    return Signal(symbol, OrderSide.SELL, 0.7, f"Downtrend detected (momentum: {momentum:.1f}%)", broker)
                    
            elif strategy == 'scalping':
                # Scalping - ultra sensitive, quick in/out
                if momentum > 0.15 and not current_position:
                    return Signal(symbol, OrderSide.BUY, 0.4, f"Scalp entry (+{momentum:.2f}%)", broker)
                elif momentum < -0.1 and current_position:
                    return Signal(symbol, OrderSide.SELL, 0.4, f"Scalp exit ({momentum:.2f}%)", broker)
                # Quick reversal trades
                elif sma_short < sma_long * 0.995 and current_position:
                    return Signal(symbol, OrderSide.SELL, 0.35, f"Quick scalp out", broker)
                    
            else:  # aggressive
                # Trade on any momentum - very sensitive
                if sma_short > sma_long and momentum > 0.3 and not current_position:
                    return Signal(symbol, OrderSide.BUY, 0.5, f"Aggressive entry (+{momentum:.2f}%)", broker)
                elif (sma_short < sma_long or momentum < -0.3) and current_position:
                    return Signal(symbol, OrderSide.SELL, 0.5, f"Quick exit ({momentum:.2f}%)", broker)
                # Also trade on pure momentum even without SMA crossover
                elif momentum > 0.5 and not current_position:
                    return Signal(symbol, OrderSide.BUY, 0.45, f"Momentum play (+{momentum:.2f}%)", broker)
            
            return None
            
        except Exception as e:
            logger.error(f"[SIGNAL ERROR] {symbol}: {e}")
            return None
    
    def _get_mock_price(self, symbol: str) -> float:
        """Generate realistic mock price for demo trading"""
        # Base prices for all symbols in watchlist
        base_prices = {
            # Tech Giants
            'AAPL': 175.0, 'MSFT': 330.0, 'GOOGL': 140.0, 'AMZN': 130.0,
            'META': 300.0, 'NVDA': 460.0, 'TSLA': 250.0, 'NFLX': 440.0,
            # Semiconductors
            'AMD': 150.0, 'INTC': 35.0, 'AVGO': 1200.0, 'QCOM': 150.0,
            'TXN': 180.0, 'MU': 85.0, 'AMAT': 140.0,
            # Software/SaaS
            'CRM': 220.0, 'ADBE': 480.0, 'ORCL': 110.0, 'INTU': 580.0,
            'NOW': 700.0, 'SNOW': 150.0, 'ZM': 65.0,
            # Finance
            'JPM': 180.0, 'BAC': 35.0, 'GS': 390.0, 'MS': 85.0,
            'WFC': 45.0, 'C': 55.0, 'BLK': 820.0,
            # Consumer
            'DIS': 110.0, 'NKE': 95.0, 'HD': 340.0, 'LOW': 220.0,
            'COST': 720.0, 'MCD': 280.0, 'SBUX': 85.0, 'TGT': 165.0,
            # Healthcare
            'JNJ': 155.0, 'UNH': 520.0, 'PFE': 28.0, 'ABBV': 165.0,
            'MRK': 115.0, 'LLY': 580.0,
            # ETFs
            'SPY': 520.0, 'QQQ': 440.0, 'IWM': 200.0, 'VIXY': 15.0,
            # Crypto - Major
            'BTCUSDT': 43000.0, 'ETHUSDT': 2600.0, 'BNBUSDT': 320.0,
            'SOLUSDT': 98.0, 'ADAUSDT': 0.5,
            # Crypto - Mid Cap
            'DOTUSDT': 7.5, 'MATICUSDT': 0.7, 'LINKUSDT': 14.0,
            'UNIUSDT': 7.0, 'LTCUSDT': 75.0, 'BCHUSDT': 240.0,
            'FILUSDT': 5.5, 'ETCUSDT': 25.0, 'XLMUSDT': 0.11,
            'VETUSDT': 0.03,
            # Crypto - DeFi
            'AAVEUSDT': 95.0, 'SUSHIUSDT': 1.2, 'COMPUSDT': 55.0,
            'MKRUSDT': 1650.0, 'CRVUSDT': 0.45,
            # Crypto - Layer 1s
            'ATOMUSDT': 8.5, 'NEARUSDT': 5.5, 'ALGOUSDT': 0.18,
            'FTMUSDT': 0.65, 'AVAXUSDT': 35.0,
            # Crypto - Meme/Other
            'DOGEUSDT': 0.15, 'SHIBUSDT': 0.000018, 'TRXUSDT': 0.11,
            'EOSUSDT': 0.85, 'XMRUSDT': 165.0
        }
        
        base = base_prices.get(symbol, 100.0)
        
        # Add random walk (±2% variation)
        if symbol in self.price_history and self.price_history[symbol]:
            last_price = self.price_history[symbol][-1]
            change = random.uniform(-0.02, 0.02)
            return last_price * (1 + change)
        else:
            # Initial price with small random variation
            return base * random.uniform(0.98, 1.02)
    
    def _get_position(self, symbol: str, broker: str) -> bool:
        """Check if we have a position in this symbol"""
        # In real implementation, check broker positions
        # For demo, track locally
        position_key = f"{broker}:{symbol}"
        return position_key in self.positions
    
    def _process_signals(self):
        """Process generated signals and execute trades"""
        if not self.signals_generated:
            return
        
        # Take the strongest signal
        signal = self.signals_generated.pop(0)
        
        # Check if we should trade based on confidence
        if signal.confidence < 0.6:
            return
        
        # Calculate position size
        total_value = self.balance_aggregator.get_total_capital()
        if total_value <= 0:
            return
        
        strategy = self.settings.get('strategy', 'moderate')
        if strategy == 'conservative':
            position_pct = 0.05
        elif strategy == 'moderate':
            position_pct = 0.10
        elif strategy == 'scalping':
            position_pct = 0.03  # Smaller positions for scalping (3%)
        else:  # aggressive
            position_pct = 0.15
        
        position_value = total_value * position_pct * signal.confidence
        
        # Estimate price and calculate quantity
        mock_price = self._get_mock_price(signal.symbol)
        quantity = position_value / mock_price
        
        # Round quantity appropriately
        if signal.broker == 'binance' and 'BTC' in signal.symbol:
            quantity = round(quantity, 4)
        elif signal.broker == 'binance':
            quantity = round(quantity, 2)
        else:
            quantity = int(quantity)
        
        if quantity <= 0:
            return
        
        # Execute the trade
        logger.info(f"[TRADE] Executing {signal.side.value.upper()} {quantity} {signal.symbol} "
                   f"(~${position_value:.2f}, confidence: {signal.confidence:.2f})")
        
        order = self.place_order(
            signal.symbol,
            signal.side,
            quantity,
            OrderType.MARKET,
            broker=signal.broker
        )
        
        if order:
            self.last_trade_time = time.time()
            self.today_trades += 1
            
            # Track position
            position_key = f"{signal.broker}:{signal.symbol}"
            if signal.side == OrderSide.BUY:
                self.positions[position_key] = {
                    'symbol': signal.symbol,
                    'quantity': quantity,
                    'entry_price': mock_price,
                    'broker': signal.broker,
                    'timestamp': time.time()
                }
            elif signal.side == OrderSide.SELL and position_key in self.positions:
                del self.positions[position_key]
            
            logger.info(f"[TRADE SUCCESS] Order {order['id']} executed. "
                       f"Daily trades: {self.today_trades}/{self.daily_trade_limit}")
    
    def place_order(self, symbol: str, side: OrderSide, quantity: float,
                   order_type: OrderType = OrderType.MARKET,
                   broker: str = 'alpaca', limit_price: float = None) -> Optional[Dict]:
        """Place an order through specified broker - EXECUTES REAL TRADES"""
        try:
            broker_obj = self.balance_aggregator.get_broker(broker)
            
            if not broker_obj or not broker_obj.connected:
                logger.error(f"[ORDER ERROR] {broker} not connected")
                return None
            
            # Check if broker has place_order method
            if not hasattr(broker_obj, 'place_order'):
                logger.error(f"[ORDER ERROR] {broker} does not support order placement")
                return None
            
            # Execute real order with broker
            logger.info(f"[ORDER] Executing {side.value.upper()} {quantity} {symbol} via {broker}")
            
            result = broker_obj.place_order(
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                order_type=order_type.value
            )
            
            if result:
                self.orders.append(result)
                logger.info(f"{'='*50}")
                logger.info(f"[ORDER EXECUTED] {side.value.upper()} {quantity} {symbol}")
                logger.info(f"[ORDER] Broker: {broker}, Order ID: {result['id']}")
                logger.info(f"{'='*50}")
                return result
            else:
                logger.error(f"[ORDER FAILED] {broker} returned None")
                return None
            
        except Exception as e:
            logger.error(f"[ORDER ERROR] {e}")
            return None
    
    def sell_all_positions(self, broker: str = 'all'):
        """Sell all positions"""
        logger.info(f"[ENGINE] Selling all positions for {broker}")
        
        brokers = ['alpaca', 'binance', 'ibkr'] if broker == 'all' else [broker]
        
        for b in brokers:
            broker_obj = self.balance_aggregator.get_broker(b)
            if broker_obj and broker_obj.connected:
                try:
                    if b == 'alpaca':
                        positions = broker_obj.get_positions()
                        for pos in positions:
                            self.place_order(
                                pos['symbol'], OrderSide.SELL,
                                pos['qty'], broker='alpaca'
                            )
                    
                    elif b == 'binance':
                        balances = broker_obj.get_all_balances()
                        for asset, amount in balances.items():
                            if asset not in ['USDT', 'BUSD'] and amount > 0:
                                symbol = f"{asset}USDT"
                                self.place_order(
                                    symbol, OrderSide.SELL,
                                    amount, broker='binance'
                                )
                
                except Exception as e:
                    logger.error(f"[SELL ALL ERROR] {b}: {e}")
    
    def _check_stop_losses(self):
        """Check and execute stop losses on open positions"""
        try:
            for position_key, position in list(self.positions.items()):
                symbol = position['symbol']
                entry_price = position['entry_price']
                current_price = self._get_mock_price(symbol)
                qty = position['quantity']
                broker = position['broker']
                
                if entry_price > 0:
                    loss_pct = (entry_price - current_price) / entry_price * 100
                    if loss_pct >= self.stop_loss_pct:
                        logger.warning(f"[STOP LOSS TRIGGERED] {symbol} at -{loss_pct:.2f}%")
                        self.place_order(symbol, OrderSide.SELL, qty, broker=broker)
        
        except Exception as e:
            logger.error(f"[STOP LOSS ERROR] {e}")
    
    def _check_take_profits(self):
        """Check and execute take profits on open positions"""
        try:
            for position_key, position in list(self.positions.items()):
                symbol = position['symbol']
                entry_price = position['entry_price']
                current_price = self._get_mock_price(symbol)
                qty = position['quantity']
                broker = position['broker']
                
                if entry_price > 0:
                    profit_pct = (current_price - entry_price) / entry_price * 100
                    if profit_pct >= self.take_profit_pct:
                        logger.info(f"[TAKE PROFIT TRIGGERED] {symbol} at +{profit_pct:.2f}%")
                        self.place_order(symbol, OrderSide.SELL, qty, broker=broker)
        
        except Exception as e:
            logger.error(f"[TAKE PROFIT ERROR] {e}")
    
    def _evaluate_strategies(self):
        """Legacy method - now handled in _scan_for_opportunities"""
        pass
    
    def can_place_order(self, symbol: str, quantity: float, price: float) -> bool:
        """Check if an order can be placed based on risk management"""
        total_value = self.balance_aggregator.get_total_capital()
        if total_value <= 0:
            return False
        
        position_value = quantity * price
        position_pct = (position_value / total_value) * 100
        
        if position_pct > self.max_position_pct:
            logger.warning(f"[RISK] Order exceeds max position size: {position_pct:.1f}%")
            return False
        
        return True
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        return self.balance_aggregator.get_total_capital()
    
    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'running': self.is_running,
            'mode': self.settings.get('trading_mode', 'demo'),
            'strategy': self.settings.get('strategy', 'moderate'),
            'trading_enabled': self.settings.get('trading_enabled', False),
            'positions_count': len(self.positions),
            'orders_count': len(self.orders),
            'today_trades': self.today_trades,
            'daily_limit': self.daily_trade_limit,
            'watchlist_size': sum(len(v) for v in self.watchlist.values())
        }
    
    def get_positions_summary(self) -> List[Dict]:
        """Get summary of current positions"""
        summary = []
        for position_key, position in self.positions.items():
            current_price = self._get_mock_price(position['symbol'])
            entry_price = position['entry_price']
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            summary.append({
                'symbol': position['symbol'],
                'quantity': position['quantity'],
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_pct': pnl_pct,
                'broker': position['broker']
            })
        return summary
