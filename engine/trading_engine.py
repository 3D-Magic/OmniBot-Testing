"""
Trading Engine - FULLY FUNCTIONAL REAL TRADING
Core trading logic with live order execution and real market data
"""
import threading
import time
import logging
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

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


class TradingEngine:
    """Main trading engine with risk management and live order execution"""
    
    def __init__(self, balance_aggregator, settings):
        self.balance_aggregator = balance_aggregator
        self.settings = settings
        self.is_running = False
        self.thread = None
        self.positions = {}  # Track positions locally
        self.orders = []  # Order history
        
        # Risk management settings
        self.max_position_pct = 10.0  # Max 10% per position
        self.stop_loss_pct = 5.0      # 5% stop loss
        self.take_profit_pct = 10.0   # 10% take profit
        
        # Trading state
        self.buying_enabled = True    # Can be disabled after sell-all
        self.sell_all_triggered = False
        self.min_trade_interval = 30  # 30 seconds between trades (reduced from 60)
        self.last_trade_time = 0
        
        # Trade counter (for stats only, no limit)
        self.today_trades = 0
        self.last_trade_date = datetime.now().date()
        
        # Watchlist
        self.watchlist = {
            'alpaca': settings.get('alpaca_watchlist', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']),
            'binance': settings.get('binance_watchlist', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
        }
        
        # Initialize strategy
        self.current_strategy_name = settings.get('strategy', 'swing_trading')
        self._load_strategy()
        
        logger.info(f"[ENGINE] Initialized with {len(self.watchlist['alpaca'])} stocks, {len(self.watchlist['binance'])} cryptos")
        logger.info(f"[ENGINE] Strategy: {self.current_strategy_name}")
    
    def _load_strategy(self):
        """Load the current strategy from strategies module"""
        try:
            from .strategies import get_strategy
            self.current_strategy = get_strategy(self.current_strategy_name)
            if self.current_strategy:
                logger.info(f"[ENGINE] Loaded strategy: {self.current_strategy.name}")
            else:
                logger.warning(f"[ENGINE] Strategy '{self.current_strategy_name}' not found, using default")
                self.current_strategy = None
        except Exception as e:
            logger.error(f"[ENGINE] Error loading strategy: {e}")
            self.current_strategy = None
    
    def set_strategy(self, strategy_name: str):
        """Change the trading strategy"""
        self.current_strategy_name = strategy_name
        self._load_strategy()
        self.settings.set('strategy', strategy_name)
        logger.info(f"[ENGINE] Strategy changed to: {strategy_name}")
    
    def start(self) -> bool:
        """Start the trading engine"""
        if self.is_running:
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._trading_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"[ENGINE] Trading engine started")
        logger.info(f"[ENGINE] Strategy: {self.settings.get('strategy', 'moderate')}")
        logger.info(f"[ENGINE] Buying enabled: {self.buying_enabled}")
        return True
    
    def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[ENGINE] Trading engine stopped")
    
    def enable_buying(self):
        """Re-enable buying after sell-all"""
        self.buying_enabled = True
        self.sell_all_triggered = False
        logger.info("[ENGINE] Buying re-enabled")
    
    def disable_buying(self):
        """Disable buying (after sell-all)"""
        self.buying_enabled = False
        self.sell_all_triggered = True
        logger.info("[ENGINE] Buying disabled - will only sell positions")
    
    def _trading_loop(self):
        """Main trading loop - trades continuously when markets are open"""
        loop_count = 0
        logger.info("[ENGINE] Trading loop started - continuous trading mode")
        
        while self.is_running:
            try:
                loop_count += 1
                
                # Only trade if enabled
                if not self.settings.get('trading_enabled', False):
                    time.sleep(5)
                    continue
                
                # Reset daily trade counter (for stats only)
                current_date = datetime.now().date()
                if current_date != self.last_trade_date:
                    self.today_trades = 0
                    self.last_trade_date = current_date
                    logger.info(f"[ENGINE] New trading day. Total trades yesterday: {self.today_trades}")
                
                # Check positions and manage risk (every loop)
                self._check_stop_losses()
                self._check_take_profits()
                
                # Evaluate strategies and trade (every 30 seconds = 6 loops)
                if loop_count % 6 == 0:
                    self._scan_for_opportunities()
                
                time.sleep(5)  # 5 second loop
                
            except Exception as e:
                logger.error(f"[ENGINE ERROR] {e}")
                time.sleep(10)
    
    def _scan_for_opportunities(self):
        """Scan watchlist for trading opportunities using real market data"""
        strategy = self.settings.get('strategy', 'moderate')
        
        # Check minimum interval between trades
        if time.time() - self.last_trade_time < self.min_trade_interval:
            return
        
        # Scan stocks (Alpaca) - only if buying is enabled
        if self.buying_enabled:
            broker = self.balance_aggregator.get_broker('alpaca')
            if broker and broker.connected:
                for symbol in self.watchlist['alpaca']:
                    signal = self._generate_signal(symbol, 'alpaca', strategy)
                    if signal and signal['confidence'] > 0.6:
                        self._execute_signal(signal)
        
        # Scan crypto (Binance) - only if buying is enabled
        if self.buying_enabled:
            broker = self.balance_aggregator.get_broker('binance')
            if broker and broker.connected:
                for symbol in self.watchlist['binance']:
                    signal = self._generate_signal(symbol, 'binance', strategy)
                    if signal and signal['confidence'] > 0.6:
                        self._execute_signal(signal)
    
    def _generate_signal(self, symbol: str, broker: str, strategy: str) -> Optional[Dict]:
        """
        Generate trading signal using real market data and technical analysis
        Uses the selected strategy from strategies module
        """
        try:
            broker_obj = self.balance_aggregator.get_broker(broker)
            if not broker_obj or not broker_obj.connected:
                return None
            
            # Get historical data based on strategy timeframe
            if self.current_strategy:
                data_req = self.current_strategy.get_required_data()
                timeframe = data_req.get('timeframe', '1d')
                lookback = data_req.get('lookback', 50)
            else:
                timeframe = '1d'
                lookback = 50
            
            # Get data from broker
            if broker == 'alpaca':
                # Convert timeframe for Alpaca
                alpaca_timeframe = '1Day' if timeframe == '1d' else '1Hour' if timeframe == '1h' else '15Min' if timeframe == '15m' else '5Min' if timeframe == '5m' else '1Min'
                df = broker_obj.get_bars(symbol, alpaca_timeframe, limit=lookback)
            else:  # binance
                df = broker_obj.get_klines(symbol, timeframe, limit=lookback)
            
            if df is None or len(df) < 30:
                return None
            
            # Check if we already have a position
            position_key = f"{broker}:{symbol}"
            has_position = position_key in self.positions
            
            # Use strategy from strategies module if available
            if self.current_strategy:
                signal = self.current_strategy.generate_signal(df, symbol, has_position)
                if signal:
                    # Add broker and convert side to OrderSide
                    signal['broker'] = broker
                    signal['side'] = OrderSide.BUY if signal['side'] == 'buy' else OrderSide.SELL
                    # Get current price for the signal
                    if broker == 'alpaca':
                        quote = broker_obj.get_latest_trade(symbol)
                        signal['price'] = quote.get('price', df.iloc[-1]['close']) if quote else df.iloc[-1]['close']
                    else:
                        signal['price'] = broker_obj.get_latest_price(symbol)
                return signal
            
            # Fallback to legacy strategy logic if no strategy module loaded
            return self._generate_legacy_signal(df, symbol, broker, strategy, has_position, broker_obj)
            
        except Exception as e:
            logger.error(f"[SIGNAL ERROR] {symbol}: {e}")
            return None
    
    def _generate_legacy_signal(self, df, symbol: str, broker: str, strategy: str, has_position: bool, broker_obj) -> Optional[Dict]:
        """Fallback legacy signal generation"""
        # Calculate technical indicators
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        if pd.isna(current['sma_20']) or pd.isna(current['sma_50']) or pd.isna(current['rsi']):
            return None
        
        # Get current price
        if broker == 'alpaca':
            quote = broker_obj.get_latest_trade(symbol)
            current_price = quote.get('price', current['close']) if quote else current['close']
        else:
            current_price = broker_obj.get_latest_price(symbol)
        
        # Legacy moderate strategy
        if (prev['sma_20'] <= prev['sma_50'] and 
            current['sma_20'] > current['sma_50'] and
            current['rsi'] > 45 and
            not has_position):
            
            return {
                'symbol': symbol,
                'side': OrderSide.BUY,
                'confidence': 0.65,
                'reason': f"Golden cross + RSI {current['rsi']:.1f}",
                'broker': broker,
                'price': current_price
            }
        
        elif (prev['sma_20'] >= prev['sma_50'] and 
              current['sma_20'] < current['sma_50'] and 
              current['rsi'] < 55 and
              has_position):
            
            return {
                'symbol': symbol,
                'side': OrderSide.SELL,
                'confidence': 0.65,
                'reason': f"Death cross + RSI {current['rsi']:.1f}",
                'broker': broker,
                'price': current_price
            }
        
        return None
    
    def _execute_signal(self, signal: Dict):
        """Execute a trading signal"""
        try:
            symbol = signal['symbol']
            side = signal['side']
            broker = signal['broker']
            price = signal['price']
            confidence = signal['confidence']
            
            # Skip BUY signals if buying is disabled
            if side == OrderSide.BUY and not self.buying_enabled:
                logger.info(f"[BLOCKED] BUY {symbol} - buying is disabled (sell-all mode)")
                return
            
            # Get total portfolio value
            total_value = self.balance_aggregator.get_total_capital()
            if total_value <= 0:
                return
            
            # Calculate position size based on strategy
            strategy = self.settings.get('strategy', 'moderate')
            if strategy == 'conservative':
                position_pct = 0.05  # 5% per trade
            elif strategy == 'moderate':
                position_pct = 0.10  # 10% per trade
            else:  # aggressive
                position_pct = 0.15  # 15% per trade
            
            position_value = total_value * position_pct * confidence
            
            # Calculate quantity
            if price > 0:
                quantity = position_value / price
            else:
                return
            
            # Round quantity appropriately
            if broker == 'binance' and 'BTC' in symbol:
                quantity = round(quantity, 5)
            elif broker == 'binance':
                quantity = round(quantity, 4)
            else:
                quantity = int(quantity)
            
            if quantity <= 0:
                return
            
            # Execute the trade
            logger.info(f"[SIGNAL] {side.value.upper()} {symbol} - {signal['reason']}")
            
            order = self.place_order(
                symbol, side, quantity, 
                OrderType.MARKET, broker=broker
            )
            
            if order:
                self.last_trade_time = time.time()
                self.today_trades += 1
                
                # Track position
                position_key = f"{broker}:{symbol}"
                if side == OrderSide.BUY:
                    self.positions[position_key] = {
                        'symbol': symbol,
                        'quantity': quantity,
                        'entry_price': price,
                        'broker': broker,
                        'timestamp': time.time()
                    }
                elif side == OrderSide.SELL and position_key in self.positions:
                    del self.positions[position_key]
                
                logger.info(f"[TRADE] Order {order['id']} executed. Total trades today: {self.today_trades}")
        
        except Exception as e:
            logger.error(f"[EXECUTE ERROR] {e}")
    
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
                logger.info(f"[ORDER EXECUTED] {side.value.upper()} {quantity} {symbol}")
                logger.info(f"[ORDER] Broker: {broker}, ID: {result['id']}")
                logger.info(f"{'='*50}")
                return result
            else:
                logger.error(f"[ORDER FAILED] {broker} returned None")
                return None
                
        except Exception as e:
            logger.error(f"[ORDER ERROR] {e}")
            return None
    
    def sell_all_positions(self, broker: str = 'all'):
        """Sell all positions and disable buying"""
        logger.info(f"[ENGINE] Selling all positions for {broker}")
        
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
        
        # Disable buying after selling all
        self.disable_buying()
        logger.info(f"[ENGINE] Sold {sold_count} positions. Buying disabled.")
        
        return {'success': True, 'sold_count': sold_count, 'buying_disabled': True}
    
    def sell_all_if_profitable(self, broker: str = 'all'):
        """Sell all positions only if they are profitable, then disable buying"""
        logger.info(f"[ENGINE] Checking positions for profitability before sell-all")
        
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
                            
                            # Get current price
                            quote = broker_obj.get_latest_trade(symbol)
                            current_price = quote.get('price', entry_price) if quote else entry_price
                            
                            # Check if profitable
                            if entry_price > 0 and current_price > entry_price:
                                profit_pct = (current_price - entry_price) / entry_price * 100
                                logger.info(f"[SELL-ALL] {symbol} is profitable (+{profit_pct:.2f}%), selling...")
                                result = self.place_order(
                                    symbol, OrderSide.SELL, qty, broker='alpaca'
                                )
                                if result:
                                    sold_count += 1
                            else:
                                loss_pct = (entry_price - current_price) / entry_price * 100 if entry_price > 0 else 0
                                logger.info(f"[SELL-ALL] {symbol} not profitable (-{loss_pct:.2f}%), skipping")
                                skipped_count += 1
                    
                    elif b == 'binance':
                        # Similar logic for Binance
                        balances = broker_obj.get_all_balances()
                        for asset, amount in balances.items():
                            if asset not in ['USDT', 'BUSD'] and amount > 0:
                                symbol = f"{asset}USDT"
                                current_price = broker_obj.get_latest_price(symbol)
                                # For Binance, we'd need entry price tracking
                                # For now, sell if we have a position
                                result = self.place_order(
                                    symbol, OrderSide.SELL, amount, broker='binance'
                                )
                                if result:
                                    sold_count += 1
                
                except Exception as e:
                    logger.error(f"[SELL ALL ERROR] {b}: {e}")
        
        # Disable buying after sell-all attempt
        self.disable_buying()
        logger.info(f"[ENGINE] Sell-all complete: {sold_count} sold, {skipped_count} skipped. Buying disabled.")
        
        return {
            'success': True, 
            'sold_count': sold_count, 
            'skipped_count': skipped_count,
            'buying_disabled': True
        }
    
    def _check_stop_losses(self):
        """Check and execute stop losses on open positions"""
        try:
            for position_key, position in list(self.positions.items()):
                symbol = position['symbol']
                entry_price = position['entry_price']
                qty = position['quantity']
                broker = position['broker']
                
                # Get current price
                broker_obj = self.balance_aggregator.get_broker(broker)
                if not broker_obj or not broker_obj.connected:
                    continue
                
                if broker == 'alpaca':
                    quote = broker_obj.get_latest_trade(symbol)
                    current_price = quote.get('price', entry_price) if quote else entry_price
                else:  # binance
                    current_price = broker_obj.get_latest_price(symbol)
                
                if entry_price > 0 and current_price > 0:
                    loss_pct = (entry_price - current_price) / entry_price * 100
                    if loss_pct >= self.stop_loss_pct:
                        logger.warning(f"[STOP LOSS] {symbol} at -{loss_pct:.2f}%")
                        self.place_order(symbol, OrderSide.SELL, qty, broker=broker)
                        del self.positions[position_key]
        
        except Exception as e:
            logger.error(f"[STOP LOSS ERROR] {e}")
    
    def _check_take_profits(self):
        """Check and execute take profits on open positions"""
        try:
            for position_key, position in list(self.positions.items()):
                symbol = position['symbol']
                entry_price = position['entry_price']
                qty = position['quantity']
                broker = position['broker']
                
                # Get current price
                broker_obj = self.balance_aggregator.get_broker(broker)
                if not broker_obj or not broker_obj.connected:
                    continue
                
                if broker == 'alpaca':
                    quote = broker_obj.get_latest_trade(symbol)
                    current_price = quote.get('price', entry_price) if quote else entry_price
                else:  # binance
                    current_price = broker_obj.get_latest_price(symbol)
                
                if entry_price > 0 and current_price > 0:
                    profit_pct = (current_price - entry_price) / entry_price * 100
                    if profit_pct >= self.take_profit_pct:
                        logger.info(f"[TAKE PROFIT] {symbol} at +{profit_pct:.2f}%")
                        self.place_order(symbol, OrderSide.SELL, qty, broker=broker)
                        del self.positions[position_key]
        
        except Exception as e:
            logger.error(f"[TAKE PROFIT ERROR] {e}")
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        return self.balance_aggregator.get_total_capital()
    
    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'running': self.is_running,
            'mode': self.settings.get('trading_mode', 'demo'),
            'strategy': self.current_strategy_name,
            'strategy_name': self.current_strategy.name if self.current_strategy else 'Legacy',
            'trading_enabled': self.settings.get('trading_enabled', False),
            'buying_enabled': self.buying_enabled,
            'sell_all_triggered': self.sell_all_triggered,
            'positions_count': len(self.positions),
            'orders_count': len(self.orders),
            'today_trades': self.today_trades
        }
