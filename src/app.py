#!/usr/bin/env python3
"""
OMNIBOT TITAN v2.7.2
Professional Algorithmic Trading Bot
Supports: Alpaca, Binance, PayPal
Features: Real order execution, touch keyboard, kiosk mode

Author: OMNIBOT Team
License: MIT
Repository: https://github.com/omnibot/omnibot-titan
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, jsonify, request, session, redirect
from flask_socketio import SocketIO, emit

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CONFIGURATION ============
class Settings:
    """Application settings manager with persistence"""
    
    def __init__(self, config_path=None):
        self.filepath = config_path or os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
        self._data = {}
        self._load()
    
    def _load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    self._data = json.load(f)
                logger.info(f"Settings loaded from {self.filepath}")
            else:
                logger.warning("Settings file not found, using defaults")
                self._data = self._defaults()
                self.save()
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._data = self._defaults()
    
    def _defaults(self):
        return {
            'dashboard_host': '0.0.0.0',
            'dashboard_port': 8081,
            'trading_enabled': False,
            'trading_mode': 'moderate',
            'active_strategy': 'swing_trading',
            'alpaca_watchlist': ['AAPL','MSFT','GOOGL','AMZN','TSLA'],
            'binance_watchlist': ['BTC','ETH','BNB','SOL','ADA'],
            'brokers': {
                'alpaca': {
                    'enabled': False,
                    'paper': True,
                    'api_key': '',
                    'secret_key': ''
                },
                'binance': {
                    'enabled': False,
                    'testnet': True,
                    'api_key': '',
                    'secret_key': ''
                },
                'paypal': {
                    'enabled': False,
                    'sandbox': True,
                    'client_id': '',
                    'client_secret': ''
                }
            },
            'risk': {
                'stop_loss_pct': 5.0,
                'take_profit_pct': 10.0,
                'max_position_pct': 10.0,
                'max_daily_loss': 100.0
            },
            'strategies': {
                'scalping': {'enabled': True, 'allocation': 10},
                'day_trading': {'enabled': True, 'allocation': 20},
                'swing_trading': {'enabled': True, 'allocation': 30},
                'momentum': {'enabled': False, 'allocation': 15},
                'mean_reversion': {'enabled': False, 'allocation': 15},
                'breakout': {'enabled': False, 'allocation': 10}
            }
        }
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def set(self, key, value):
        self._data[key] = value
        return self.save()
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self._data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get_all(self):
        return self._data.copy()
    
    def get_broker_config(self, broker_name):
        return self._data.get('brokers', {}).get(broker_name, {})
    
    def update_broker_config(self, broker_name, config):
        if 'brokers' not in self._data:
            self._data['brokers'] = {}
        self._data['brokers'][broker_name] = config
        return self.save()


# ============ BROKERS ============
class AlpacaBroker:
    """Alpaca Trading API Integration"""
    
    def __init__(self, api_key=None, secret_key=None, paper=True):
        self.api_key = api_key or ''
        self.secret_key = secret_key or ''
        self.paper = paper
        self.connected = False
        self.trading_client = None
        self.last_error = None
    
    def update_credentials(self, api_key, secret_key, paper=None):
        self.api_key = api_key or self.api_key
        self.secret_key = secret_key or self.secret_key
        if paper is not None:
            self.paper = paper
        self.connected = False
        return self.connect()
    
    def connect(self):
        if not self.api_key or not self.secret_key:
            self.last_error = "API keys not configured"
            return False
        try:
            from alpaca.trading.client import TradingClient
            self.trading_client = TradingClient(self.api_key, self.secret_key, paper=self.paper)
            account = self.trading_client.get_account()
            self.connected = True
            logger.info(f"Alpaca {'Paper' if self.paper else 'Live'} connected")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Alpaca connect error: {e}")
            return False
    
    def get_balance(self):
        if not self.connected:
            return {'cash': 0, 'buying_power': 0, 'equity': 0}
        try:
            acc = self.trading_client.get_account()
            return {
                'cash': float(acc.cash),
                'buying_power': float(acc.buying_power),
                'equity': float(acc.equity),
                'portfolio_value': float(acc.portfolio_value)
            }
        except Exception as e:
            logger.error(f"Alpaca balance error: {e}")
            return {'cash': 0, 'buying_power': 0, 'equity': 0}
    
    def get_positions(self):
        if not self.connected:
            return []
        try:
            positions = self.trading_client.get_all_positions()
            return [{
                'symbol': p.symbol,
                'qty': float(p.qty),
                'avg_entry_price': float(p.avg_entry_price),
                'current_price': float(p.current_price),
                'market_value': float(p.market_value),
                'unrealized_pl': float(p.unrealized_pl),
                'unrealized_plpc': float(p.unrealized_plpc) * 100
            } for p in positions]
        except Exception as e:
            logger.error(f"Alpaca positions error: {e}")
            return []
    
    def submit_order(self, symbol, qty, side, order_type='market', limit_price=None):
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            side_enum = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            if order_type.lower() == 'limit' and limit_price is not None:
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=side_enum,
                    time_in_force=TimeInForce.GTC,
                    limit_price=limit_price
                )
            else:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=side_enum,
                    time_in_force=TimeInForce.DAY
                )
            order = self.trading_client.submit_order(order_request)
            logger.info(f"Order submitted: {side} {qty} {symbol}")
            return {
                'success': True,
                'order_id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'status': order.status
            }
        except Exception as e:
            logger.error(f"Alpaca order error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_latest_price(self, symbol):
        if not self.connected:
            return None
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestQuoteRequest
            client = StockHistoricalDataClient(self.api_key, self.secret_key)
            req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = client.get_stock_latest_quote(req)
            q = quote[symbol]
            price = getattr(q, 'ask_price', getattr(q, 'ap', None))
            if price is None:
                price = getattr(q, 'bid_price', getattr(q, 'bp', None))
            return float(price) if price else None
        except Exception as e:
            logger.error(f"Alpaca price error: {e}")
            return None
    
    def get_bars(self, symbol, timeframe='1Min', limit=100):
        if not self.connected:
            try:
                import pandas as pd
                return pd.DataFrame()
            except ImportError:
                return None
        try:
            import pandas as pd
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            client = StockHistoricalDataClient(self.api_key, self.secret_key)
            tf = TimeFrame.Minute if timeframe in ('1Min','1m','1min') else TimeFrame.Hour if timeframe in ('1H','1h') else TimeFrame.Day
            req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, limit=limit)
            bars = client.get_stock_bars(req)
            df = bars.df.reset_index()
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            elif 'timestamp' not in df.columns and 'symbol' in df.columns:
                df = df.drop(columns=['symbol']).set_index('timestamp')
            return df
        except Exception as e:
            logger.error(f"Alpaca bars error: {e}")
            try:
                import pandas as pd
                return pd.DataFrame()
            except ImportError:
                return None
    
    def get_orders(self, status='all'):
        if not self.connected:
            return []
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            
            if status == 'open':
                request_params = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            elif status == 'closed':
                request_params = GetOrdersRequest(status=QueryOrderStatus.CLOSED)
            else:
                request_params = GetOrdersRequest(status=QueryOrderStatus.ALL)
            
            orders = self.trading_client.get_orders(request_params)
            return [{
                'order_id': o.id,
                'symbol': o.symbol,
                'qty': o.qty,
                'side': o.side,
                'type': o.type,
                'status': o.status,
                'filled_qty': o.filled_qty,
                'filled_avg_price': o.filled_avg_price,
                'created_at': str(o.created_at)
            } for o in orders]
        except Exception as e:
            logger.error(f"Alpaca orders error: {e}")
            return []
    
    def cancel_order(self, order_id):
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        try:
            self.trading_client.cancel_order(order_id)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def close_position(self, symbol):
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        try:
            self.trading_client.close_position(symbol)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class BinanceBroker:
    """Binance Trading API Integration"""
    
    def __init__(self, api_key=None, secret_key=None, testnet=True):
        self.api_key = api_key or ''
        self.secret_key = secret_key or ''
        self.testnet = testnet
        self.connected = False
        self.client = None
        self.last_error = None
    
    def update_credentials(self, api_key, secret_key, testnet=None):
        self.api_key = api_key or self.api_key
        self.secret_key = secret_key or self.secret_key
        if testnet is not None:
            self.testnet = testnet
        self.connected = False
        return self.connect()
    
    def connect(self):
        if not self.api_key or not self.secret_key:
            self.last_error = "API keys not configured"
            return False
        try:
            from binance.client import Client
            self.client = Client(self.api_key, self.secret_key, testnet=self.testnet)
            account = self.client.get_account()
            self.connected = True
            logger.info(f"Binance {'Testnet' if self.testnet else 'Live'} connected")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Binance connect error: {e}")
            return False
    
    def get_balance(self):
        if not self.connected:
            return {'usdt': 0}
        try:
            account = self.client.get_account()
            balances = {}
            for b in account['balances']:
                asset = b['asset']
                free = float(b['free'])
                locked = float(b['locked'])
                total = free + locked
                if total > 0:
                    balances[asset.lower()] = total
            return balances
        except Exception as e:
            logger.error(f"Binance balance error: {e}")
            return {'usdt': 0}
    
    def get_positions(self):
        if not self.connected:
            return []
        try:
            account = self.client.get_account()
            positions = []
            for b in account['balances']:
                total = float(b['free']) + float(b['locked'])
                if total > 0 and b['asset'] != 'USDT':
                    positions.append({
                        'symbol': b['asset'],
                        'qty': total,
                        'asset': b['asset']
                    })
            return positions
        except Exception as e:
            logger.error(f"Binance positions error: {e}")
            return []
    
    def submit_order(self, symbol, qty, side, order_type='MARKET', limit_price=None):
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        try:
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"
            if order_type.upper() == 'LIMIT' and limit_price is not None:
                if side.upper() == 'BUY':
                    order = self.client.order_limit_buy(symbol=symbol, quantity=qty, price=limit_price)
                else:
                    order = self.client.order_limit_sell(symbol=symbol, quantity=qty, price=limit_price)
            else:
                order = self.client.order_market(
                    symbol=symbol,
                    side=side.upper(),
                    quantity=qty
                )
            logger.info(f"Binance order submitted: {side} {qty} {symbol}")
            return {
                'success': True,
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'status': order['status']
            }
        except Exception as e:
            logger.error(f"Binance order error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_latest_price(self, symbol):
        if not self.connected:
            return None
        try:
            sym = symbol if symbol.endswith('USDT') else f"{symbol}USDT"
            ticker = self.client.get_symbol_ticker(symbol=sym)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Binance price error: {e}")
            return None
    
    def get_bars(self, symbol, interval='1m', limit=100):
        if not self.connected:
            try:
                import pandas as pd
                return pd.DataFrame()
            except ImportError:
                return None
        try:
            import pandas as pd
            sym = symbol if symbol.endswith('USDT') else f"{symbol}USDT"
            klines = self.client.get_klines(symbol=sym, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=['open_time','open','high','low','close','volume','close_time','quote_asset_volume','number_of_trades','taker_buy_base_asset_volume','taker_buy_quote_asset_volume','ignore'])
            for col in ['open','high','low','close','volume']:
                df[col] = df[col].astype(float)
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df = df.set_index('open_time')
            return df
        except Exception as e:
            logger.error(f"Binance bars error: {e}")
            try:
                import pandas as pd
                return pd.DataFrame()
            except ImportError:
                return None
    
    def get_orders(self, symbol=None):
        if not self.connected:
            return []
        try:
            if symbol:
                orders = self.client.get_all_orders(symbol=symbol)
            else:
                orders = []
            return [{
                'order_id': o['orderId'],
                'symbol': o['symbol'],
                'qty': o['origQty'],
                'side': o['side'],
                'type': o['type'],
                'status': o['status'],
                'price': o['price']
            } for o in orders]
        except Exception as e:
            logger.error(f"Binance orders error: {e}")
            return []


class PayPalWallet:
    """PayPal integration"""
    
    def __init__(self, client_id=None, client_secret=None, sandbox=True):
        self.client_id = client_id or ''
        self.client_secret = client_secret or ''
        self.sandbox = sandbox
        self.connected = False
        self.access_token = None
    
    def update_credentials(self, client_id, client_secret, sandbox=None):
        self.client_id = client_id or self.client_id
        self.client_secret = client_secret or self.client_secret
        if sandbox is not None:
            self.sandbox = sandbox
        self.connected = False
        return self.connect()
    
    def connect(self):
        if not self.client_id:
            self.connected = True
            return True
        try:
            import requests
            url = "https://api-m.sandbox.paypal.com/v1/oauth2/token" if self.sandbox else "https://api-m.paypal.com/v1/oauth2/token"
            response = requests.post(url, auth=(self.client_id, self.client_secret), data={'grant_type': 'client_credentials'})
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                self.connected = True
                return True
        except Exception as e:
            logger.error(f"PayPal connect error: {e}")
        return False
    
    def get_balance(self):
        if not self.connected:
            return {'usd': 0}
        if not self.access_token:
            return {'usd': 1000.0}
        try:
            import requests
            url = "https://api-m.sandbox.paypal.com/v1/reporting/balances" if self.sandbox else "https://api-m.paypal.com/v1/reporting/balances"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                balances = response.json().get('balances', [])
                for b in balances:
                    if b.get('currency') == 'USD':
                        return {'usd': float(b.get('available_balance', {}).get('value', 0))}
            return {'usd': 0}
        except Exception as e:
            logger.error(f"PayPal balance error: {e}")
            return {'usd': 0}
    
    def get_positions(self):
        return []
    
    def get_orders(self):
        return []


# ============ BALANCE AGGREGATOR ============
class BalanceAggregator:
    """Aggregate balances from all brokers"""
    
    def __init__(self):
        self.brokers = {}
    
    def add_broker(self, name, broker):
        self.brokers[name] = broker
    
    def reconnect_broker(self, name, settings_obj):
        broker = self.brokers.get(name)
        if not broker:
            return False
        
        config = settings_obj.get_broker_config(name)
        
        if name == 'alpaca':
            return broker.update_credentials(
                config.get('api_key'),
                config.get('secret_key'),
                config.get('paper', True)
            )
        elif name == 'binance':
            return broker.update_credentials(
                config.get('api_key'),
                config.get('secret_key'),
                config.get('testnet', True)
            )
        elif name == 'paypal':
            return broker.update_credentials(
                config.get('client_id'),
                config.get('client_secret'),
                config.get('sandbox', True)
            )
        return False
    
    def get_total_balance(self):
        """Return total portfolio value in USD. Includes all connected brokers (paper, testnet, live)."""
        total = 0
        for name, broker in self.brokers.items():
            try:
                bal = broker.get_balance()
                if isinstance(bal, dict):
                    if name == 'alpaca':
                        total += bal.get('portfolio_value', 0)
                    elif name == 'binance':
                        total += self._value_binance_usd(broker, bal)
                    elif name == 'paypal':
                        total += bal.get('usd', 0)
                    else:
                        total += sum(v for v in bal.values() if isinstance(v, (int, float)))
            except Exception as e:
                logger.error(f"Balance error for {name}: {e}")
        return total
    
    def _value_binance_usd(self, broker, balances):
        """Convert Binance asset balances to USD equivalent. Uses batch price lookup."""
        total_usd = 0.0
        stablecoins = {'usdt', 'usdc', 'busd', 'fdusd', 'tusd'}
        try:
            all_tickers = {t['symbol']: float(t['price']) for t in broker.client.get_all_tickers()}
        except Exception:
            return 0.0
        for asset, qty in balances.items():
            if not isinstance(qty, (int, float)) or qty <= 0:
                continue
            asset_lower = asset.lower()
            if asset_lower in stablecoins:
                total_usd += qty
            else:
                pair = f"{asset.upper()}USDT"
                price = all_tickers.get(pair, 0)
                if price > 0:
                    value = qty * price
                    if value > 1.0:
                        total_usd += value
        return total_usd
    
    def get_all_balances(self):
        result = {}
        for name, broker in self.brokers.items():
            try:
                result[name] = broker.get_balance()
            except Exception as e:
                logger.error(f"Balance error for {name}: {e}")
                result[name] = {}
        return result
    
    def get_portfolio_breakdown(self):
        """Return detailed portfolio breakdown per broker."""
        breakdown = {
            'total': 0,
            'alpaca': 0,
            'binance_live': 0,
            'binance_testnet': 0,
            'paypal': 0
        }
        for name, broker in self.brokers.items():
            try:
                bal = broker.get_balance()
                if not isinstance(bal, dict):
                    continue
                if name == 'alpaca':
                    val = bal.get('portfolio_value', 0)
                    breakdown['alpaca'] = val
                    breakdown['total'] += val
                elif name == 'binance':
                    usd_val = self._value_binance_usd(broker, bal)
                    if getattr(broker, 'testnet', False):
                        breakdown['binance_testnet'] = usd_val
                    else:
                        breakdown['binance_live'] = usd_val
                    breakdown['total'] += usd_val
                elif name == 'paypal':
                    val = bal.get('usd', 0)
                    breakdown['paypal'] = val
                    breakdown['total'] += val
            except Exception as e:
                logger.error(f"Portfolio breakdown error for {name}: {e}")
        return breakdown
    
    def get_all_positions(self):
        all_positions = []
        for name, broker in self.brokers.items():
            try:
                positions = broker.get_positions()
                for p in positions:
                    p['broker'] = name
                    all_positions.append(p)
            except Exception as e:
                logger.error(f"Positions error for {name}: {e}")
        return all_positions


# ============ TRADING ENGINE ============
class TradingEngine:
    """Main trading engine with indicator-driven automated trading"""
    
    def __init__(self, balance_aggregator, settings):
        self.balance_aggregator = balance_aggregator
        self.settings = settings
        self.running = False
        self.thread = None
        self.monitor_thread = None
        self.daily_pnl = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.positions = {}
        self.orders = []
        self.trade_history = []
        self.last_trade_time = {}
        self.open_orders = {}
        self.scan_log = []  # Recent scan results for visibility
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._trading_loop, daemon=True)
            self.thread.start()
            self.monitor_thread = threading.Thread(target=self._monitor_positions, daemon=True)
            self.monitor_thread.start()
            logger.info("Trading engine started")
    
    def stop(self):
        self.running = False
        logger.info("Trading engine stopped")
    
    def get_status(self):
        return {
            'running': self.running,
            'balance': self.balance_aggregator.get_total_balance(),
            'strategy': self.settings.get('active_strategy', 'swing_trading'),
            'daily_pnl': self.daily_pnl,
            'total_trades': self.total_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        }
    
    def _get_broker(self):
        alpaca = self.balance_aggregator.brokers.get('alpaca')
        if alpaca and alpaca.connected:
            return alpaca, 'alpaca'
        binance = self.balance_aggregator.brokers.get('binance')
        if binance and binance.connected:
            return binance, 'binance'
        return None, None
    
    def _get_watchlist(self):
        broker, name = self._get_broker()
        if name == 'alpaca':
            return self.settings.get('alpaca_watchlist', ['AAPL','MSFT','GOOGL','AMZN','TSLA'])
        if name == 'binance':
            return self.settings.get('binance_watchlist', ['BTC','ETH','BNB','SOL','ADA'])
        return []
    
    def _get_trading_params(self):
        """Map active_strategy to trading parameters. Unifies strategy UI with engine behavior."""
        strategy = self.settings.get('active_strategy', 'swing_trading')
        # Strategy → (mode_label, threshold, sleep_seconds, cooldown_seconds)
        mapping = {
            'scalping':        ('hft',         0.0,  30,  60),
            'day_trading':     ('aggressive',  0.5,  60,  300),
            'swing_trading':   ('moderate',    1.5,  120, 300),
            'momentum':        ('aggressive',  0.5,  60,  300),
            'mean_reversion':  ('moderate',    1.5,  120, 300),
            'breakout':        ('aggressive',  0.5,  60,  300),
            # Legacy trading_mode fallbacks
            'conservative':    ('conservative',2.5,  300, 300),
            'moderate':        ('moderate',    1.5,  120, 300),
            'aggressive':      ('aggressive',  0.5,  60,  300),
            'hft':             ('hft',         0.0,  30,  60),
        }
        return mapping.get(strategy, ('moderate', 1.5, 120, 300))
    
    def _trading_loop(self):
        while self.running:
            try:
                evaluated = False
                for name, broker in self.balance_aggregator.brokers.items():
                    if not broker or not broker.connected:
                        continue
                    if name == 'alpaca' and not self._is_us_market_open():
                        logger.info("US market closed — skipping Alpaca evaluation")
                        continue
                    if name == 'paypal':
                        continue
                    self._evaluate_broker(broker, name)
                    evaluated = True
                if not evaluated:
                    logger.warning("No eligible broker evaluated this cycle")
                _, _, sleep_secs, _ = self._get_trading_params()
                time.sleep(sleep_secs)
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(60)
    
    def _evaluate_broker(self, broker, broker_name):
        watchlist = self.settings.get(f'{broker_name}_watchlist', [])
        if broker_name == 'alpaca' and not watchlist:
            watchlist = ['AAPL','MSFT','GOOGL','AMZN','TSLA']
        if broker_name == 'binance' and not watchlist:
            watchlist = ['BTC','ETH','BNB','SOL','ADA']
        if not watchlist:
            return
        mode, threshold, _, cooldown = self._get_trading_params()
        logger.info(f"Evaluating {len(watchlist)} symbols on {broker_name.upper()} (mode={mode}, threshold={threshold})")
        for symbol in watchlist:
            if time.time() - self.last_trade_time.get(symbol, 0) < cooldown:
                continue
            tf = '1Min' if broker_name == 'alpaca' else '1m'
            result = self._analyze_symbol(broker, symbol, tf)
            self.scan_log.append({'time': datetime.now().isoformat(), 'symbol': symbol, 'broker': broker_name, **result})
            self.scan_log = self.scan_log[-200:]
            if result.get('signal') and result.get('score', 0) >= threshold:
                score = result['score']
                logger.info(f"BUY SIGNAL on {broker_name}/{symbol}: score={score:.2f} (need {threshold})")
                self._execute_buy(broker, broker_name, {
                    'symbol': symbol,
                    'confidence': min(score / 5.0, 0.99),
                    'price': result['price'],
                    'signals': result['triggered']
                })
            else:
                reason = result.get('reason', '')
                if reason:
                    logger.info(f"No signal on {broker_name}/{symbol}: {reason}")
                else:
                    logger.info(f"No signal on {broker_name}/{symbol}: score={result.get('score',0):.2f} ({result.get('triggered',[])})")
    
    def _is_us_market_open(self):
        from zoneinfo import ZoneInfo
        et = ZoneInfo('America/New_York')
        now = datetime.now(et)
        if now.weekday() >= 5:
            return False
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now <= market_close
    

    
    def _analyze_symbol(self, broker, symbol, timeframe='1Min'):
        try:
            bars = broker.get_bars(symbol, timeframe, 100)
            if bars is None or getattr(bars, 'empty', True) or len(bars) < 50:
                return {'signal': False, 'reason': 'insufficient_data', 'score': 0, 'price': 0}
            bars = self._calculate_indicators(bars)
            current = bars.iloc[-1]
            prev = bars.iloc[-2]
            price = broker.get_latest_price(symbol)
            if not price:
                return {'signal': False, 'reason': 'no_price', 'score': 0, 'price': 0}
            
            strategy = self.settings.get('active_strategy', 'swing_trading')
            score, triggered = self._score_for_strategy(strategy, current, prev, bars)
            
            # Global filters — never buy overbought or in dead markets
            rsi = current.get('rsi', 50)
            close = current['close']
            bb_low = current.get('bb_lower', close)
            bb_high = current.get('bb_upper', close)
            bb_pct = (close - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
            atr = current.get('atr', close * 0.01)
            atr_pct = atr / close * 100
            
            if rsi > 65:
                return {'signal': False, 'reason': 'overbought', 'score': 0, 'price': price, 'triggered': ['rsi_overbought'], 'indicators': {}}
            if bb_pct > 0.85:
                return {'signal': False, 'reason': 'near_bb_upper', 'score': 0, 'price': price, 'triggered': ['bb_upper'], 'indicators': {}}
            if atr_pct < 0.05:
                score *= 0.5
                triggered.append('low_volatility')
            
            return {
                'signal': score > 0,
                'score': score,
                'price': price,
                'triggered': triggered,
                'indicators': {
                    'sma_20': round(current.get('sma_20',0), 2),
                    'sma_50': round(current.get('sma_50',0), 2),
                    'macd': round(current.get('macd',0), 4),
                    'macd_signal': round(current.get('macd_signal',0), 4),
                    'rsi': round(rsi, 2),
                    'roc': round(current.get('roc',0), 2),
                    'bb_pct': round(bb_pct, 2),
                    'atr_pct': round(atr_pct, 2)
                }
            }
        except Exception as e:
            logger.error(f"Analyze error {symbol}: {e}")
            return {'signal': False, 'reason': 'exception', 'score': 0, 'price': 0}
    
    def _score_for_strategy(self, strategy, current, prev, bars):
        """Strategy-aware buy scoring. Higher score = stronger dip to buy."""
        score = 0.0
        triggered = []
        
        # Common indicator values
        sma20 = current.get('sma_20', 0)
        sma50 = current.get('sma_50', 0)
        ema12 = current.get('ema_12', 0)
        ema26 = current.get('ema_26', 0)
        macd = current.get('macd', 0)
        macd_sig = current.get('macd_signal', 0)
        macd_hist = current.get('macd_hist', 0)
        prev_hist = prev.get('macd_hist', macd_hist)
        rsi = current.get('rsi', 50)
        roc = current.get('roc', 0)
        close = current['close']
        bb_low = current.get('bb_lower', close)
        bb_high = current.get('bb_upper', close)
        bb_pct = (close - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
        atr_pct = current.get('atr', close * 0.01) / close * 100
        
        if strategy == 'scalping':
            # Fast EMA crossover
            if ema12 > ema26:
                score += 0.3; triggered.append('ema_bullish')
            # MACD histogram turning up
            if macd_hist > 0 and macd_hist > prev_hist:
                score += 0.4; triggered.append('macd_hist_up')
            # Slight oversold
            if rsi < 45:
                score += 0.5; triggered.append('rsi_dip')
            elif rsi < 55:
                score += 0.2; triggered.append('rsi_fair')
            # Near lower BB
            if bb_pct < 0.3:
                score += 0.4; triggered.append('bb_lower_zone')
            # Positive ROC
            if roc > 0:
                score += 0.2; triggered.append('roc_positive')
        
        elif strategy == 'day_trading':
            # SMA alignment
            if sma20 > sma50:
                score += 0.4; triggered.append('sma_bullish')
            # MACD confirmation
            if macd > macd_sig:
                score += 0.4; triggered.append('macd_bullish')
            # RSI dip
            if rsi < 40:
                score += 0.6; triggered.append('rsi_oversold')
            elif rsi < 50:
                score += 0.3; triggered.append('rsi_below_50')
            # BB lower touch
            if bb_pct < 0.25:
                score += 0.5; triggered.append('bb_lower')
            # Momentum
            if roc > 0.5:
                score += 0.3; triggered.append('roc_positive')
        
        elif strategy == 'swing_trading':
            # Strong trend
            if sma20 > sma50:
                score += 0.5; triggered.append('sma_bullish')
            # MACD bullish
            if macd > macd_sig and macd_hist > prev_hist:
                score += 0.5; triggered.append('macd_expanding')
            # Deep oversold
            if rsi < 35:
                score += 0.8; triggered.append('rsi_deep_oversold')
            elif rsi < 45:
                score += 0.4; triggered.append('rsi_oversold')
            # BB lower
            if bb_pct < 0.2:
                score += 0.6; triggered.append('bb_lower')
            # Positive ROC
            if roc > 0:
                score += 0.3; triggered.append('roc_positive')
        
        elif strategy == 'momentum':
            # Strong trend required
            if sma20 > sma50:
                score += 0.6; triggered.append('sma_bullish')
            # MACD expanding
            if macd > macd_sig and macd_hist > prev_hist:
                score += 0.5; triggered.append('macd_momentum')
            # RSI in healthy zone (not overbought, not dead)
            if 35 < rsi < 55:
                score += 0.4; triggered.append('rsi_momentum_zone')
            elif rsi < 35:
                score += 0.2; triggered.append('rsi_oversold')
            # Strong ROC
            if roc > 1.0:
                score += 0.5; triggered.append('roc_strong')
            elif roc > 0:
                score += 0.2; triggered.append('roc_positive')
            # Pullback to EMA 12
            if close > ema12 * 0.98:
                score += 0.3; triggered.append('above_ema12')
        
        elif strategy == 'mean_reversion':
            # Extreme oversold
            if rsi < 25:
                score += 1.2; triggered.append('rsi_extreme')
            elif rsi < 30:
                score += 0.8; triggered.append('rsi_deep_oversold')
            elif rsi < 40:
                score += 0.4; triggered.append('rsi_oversold')
            # Deep BB lower
            if bb_pct < 0.05:
                score += 0.8; triggered.append('bb_extreme')
            elif bb_pct < 0.15:
                score += 0.5; triggered.append('bb_lower')
            # MACD turning up
            if macd_hist > prev_hist:
                score += 0.5; triggered.append('macd_turning')
            # Deeply negative ROC (ready to bounce)
            if roc < -2.0:
                score += 0.5; triggered.append('roc_deep_negative')
            elif roc < -1.0:
                score += 0.3; triggered.append('roc_negative')
            elif roc > 0:
                score += 0.2; triggered.append('roc_bouncing')
        
        elif strategy == 'breakout':
            # Trend alignment
            if sma20 > sma50:
                score += 0.5; triggered.append('sma_bullish')
            # Price above middle BB (holding support)
            if close > current.get('bb_middle', close):
                score += 0.3; triggered.append('above_bb_mid')
            # MACD bullish
            if macd > macd_sig:
                score += 0.4; triggered.append('macd_bullish')
            # RSI healthy
            if 40 < rsi < 60:
                score += 0.4; triggered.append('rsi_healthy')
            # High volatility (breakout needs expansion)
            if atr_pct > 1.0:
                score += 0.5; triggered.append('atr_expansion')
            elif atr_pct > 0.5:
                score += 0.3; triggered.append('atr_elevated')
            # ROC positive
            if roc > 0.5:
                score += 0.3; triggered.append('roc_positive')
        
        else:
            # Default swing_trading fallback
            if sma20 > sma50:
                score += 0.5; triggered.append('sma_bullish')
            if macd > macd_sig:
                score += 0.5; triggered.append('macd_bullish')
            if rsi < 35:
                score += 0.8; triggered.append('rsi_oversold')
            elif rsi < 45:
                score += 0.4; triggered.append('rsi_dip')
            if bb_pct < 0.2:
                score += 0.6; triggered.append('bb_lower')
            if roc > 0:
                score += 0.3; triggered.append('roc_positive')
        
        return score, triggered
    
    def _calculate_indicators(self, bars):
        if bars is None or getattr(bars, 'empty', True):
            return bars
        bars['sma_20'] = bars['close'].rolling(window=20, min_periods=1).mean()
        bars['sma_50'] = bars['close'].rolling(window=50, min_periods=1).mean()
        bars['ema_12'] = bars['close'].ewm(span=12, adjust=False).mean()
        bars['ema_26'] = bars['close'].ewm(span=26, adjust=False).mean()
        bars['macd'] = bars['ema_12'] - bars['ema_26']
        bars['macd_signal'] = bars['macd'].ewm(span=9, adjust=False).mean()
        bars['macd_hist'] = bars['macd'] - bars['macd_signal']
        delta = bars['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss
        bars['rsi'] = 100 - (100 / (1 + rs))
        bars['roc'] = bars['close'].pct_change(periods=10) * 100
        bars['bb_middle'] = bars['close'].rolling(window=20, min_periods=1).mean()
        bb_std = bars['close'].rolling(window=20, min_periods=1).std()
        bars['bb_upper'] = bars['bb_middle'] + (bb_std * 2)
        bars['bb_lower'] = bars['bb_middle'] - (bb_std * 2)
        # ATR for volatility-based sizing
        high_low = bars['high'] - bars['low']
        high_close = (bars['high'] - bars['close'].shift()).abs()
        low_close = (bars['low'] - bars['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        bars['atr'] = tr.rolling(window=14, min_periods=1).mean()
        return bars
    
    def _get_binance_step_size(self, broker, symbol):
        """Get Binance LOT_SIZE stepSize and return precision (decimal places)."""
        try:
            sym = symbol if symbol.endswith('USDT') else f"{symbol}USDT"
            info = broker.client.get_symbol_info(sym)
            if info:
                for f in info['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step = float(f['stepSize'])
                        # Count decimal places in step size
                        step_str = f['stepSize'].rstrip('0')
                        if '.' in step_str:
                            return len(step_str.split('.')[1])
                        return 0
        except Exception:
            pass
        return 5  # Safe default
    
    def _calculate_position_size(self, broker, broker_name, symbol, price, atr=None):
        try:
            bal = broker.get_balance()
            portfolio_value = 0
            buying_power = 0
            if isinstance(bal, dict):
                if 'portfolio_value' in bal:
                    portfolio_value = bal['portfolio_value']
                    buying_power = bal.get('buying_power', portfolio_value)
                elif 'usdt' in bal:
                    portfolio_value = bal['usdt']
                    buying_power = bal['usdt']
            if portfolio_value <= 0:
                return 0
            positions = broker.get_positions()
            # Skip position limit and duplicate checks on testnet/sandbox
            is_testnet = getattr(broker, 'testnet', False) or getattr(broker, 'sandbox', False) or getattr(broker, 'paper', False)
            if not is_testnet and len(positions) >= 10:
                logger.info(f"Position size 0 for {symbol}: max 10 positions reached")
                return 0
            if not is_testnet:
                for p in positions:
                    if p.get('symbol') == symbol or p.get('symbol') == f"{symbol}USDT":
                        logger.info(f"Position size 0 for {symbol}: already holding")
                        return 0
            risk = self.settings.get('risk', {})
            max_pos_pct = risk.get('max_position_pct', 10.0) / 100.0
            max_position_value = portfolio_value * max_pos_pct
            # ATR-based risk sizing: risk 1% of portfolio per trade, sized by stop distance
            if atr and atr > 0:
                risk_amount = portfolio_value * 0.01  # Risk 1% of portfolio
                atr_multiplier = 2.0  # 2x ATR stop
                position_value = min(risk_amount / (atr * atr_multiplier / price), max_position_value)
            else:
                position_value = max_position_value
            position_value = min(position_value, buying_power * 0.95)
            if broker_name == 'alpaca':
                qty = int(position_value / price)
            else:
                qty = position_value / price
                # Round to Binance precision
                precision = self._get_binance_step_size(broker, symbol)
                qty = round(qty, precision)
            if qty <= 0:
                return 0
            logger.info(f"Position size for {symbol}: ${position_value:.2f} -> qty={qty} @ ${price:.2f}")
            return qty
        except Exception as e:
            logger.error(f"Position size error: {e}")
            return 0
    
    def _execute_buy(self, broker, broker_name, signal):
        """Execute a BUY order and track entry price for TP/SL monitoring."""
        symbol = signal['symbol']
        confidence = signal['confidence']
        price = signal['price']
        logger.info(f"BUY signal: {symbol} (confidence: {confidence:.2f}, triggered: {signal.get('signals',[])})")
        try:
            qty = self._calculate_position_size(broker, broker_name, symbol, price)
            if qty <= 0:
                return
            result = broker.submit_order(symbol, qty, 'buy')
            if result.get('success'):
                self.last_trade_time[symbol] = time.time()
                self.total_trades += 1
                self.orders.append({'broker': broker_name, 'symbol': symbol, 'qty': qty, 'side': 'buy', 'price': price, 'confidence': confidence, 'timestamp': datetime.now().isoformat(), **result})
                # Track entry price for TP/SL monitor
                key = f"{broker_name}:{symbol}"
                self.positions[key] = {
                    'broker_name': broker_name,
                    'symbol': symbol,
                    'qty': qty,
                    'entry_price': price,
                    'timestamp': time.time()
                }
                logger.info(f"BUY EXECUTED: {qty} {symbol} @ ${price:.2f}")
        except Exception as e:
            logger.error(f"Execute buy error: {e}")
    
    def _monitor_positions(self):
        """Monitor all open positions across all brokers. Sell at take-profit or stop-loss."""
        while self.running:
            try:
                tp_pct = self.settings.get('risk', {}).get('take_profit_pct', 5.0)
                sl_pct = self.settings.get('risk', {}).get('stop_loss_pct', 3.0)
                
                # Check each tracked position
                for key, pos in list(self.positions.items()):
                    broker_name = pos['broker_name']
                    symbol = pos['symbol']
                    qty = pos['qty']
                    entry_price = pos['entry_price']
                    
                    broker = self.balance_aggregator.brokers.get(broker_name)
                    if not broker or not broker.connected:
                        continue
                    
                    current_price = broker.get_latest_price(symbol)
                    if not current_price or current_price <= 0:
                        continue
                    
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                    
                    if pnl_pct >= tp_pct:
                        logger.info(f"TAKE PROFIT: {broker_name}/{symbol} +{pnl_pct:.2f}% (target {tp_pct}%)")
                        self._execute_sell(broker, broker_name, symbol, qty, current_price, reason='take_profit')
                    elif pnl_pct <= -sl_pct:
                        logger.warning(f"STOP LOSS: {broker_name}/{symbol} {pnl_pct:.2f}% (limit {-sl_pct}%)")
                        self._execute_sell(broker, broker_name, symbol, qty, current_price, reason='stop_loss')
                
                time.sleep(30)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)
    
    def _execute_sell(self, broker, broker_name, symbol, qty, price, reason=''):
        """Execute a SELL order (TP/SL only) and remove from tracked positions."""
        try:
            # Leave 0.5% buffer for fees
            sell_qty = qty * 0.995
            if broker_name != 'alpaca':
                precision = self._get_binance_step_size(broker, symbol)
                sell_qty = round(sell_qty, precision)
            if sell_qty <= 0:
                return
            result = broker.submit_order(symbol, sell_qty, 'sell')
            if result.get('success'):
                self.total_trades += 1
                self.orders.append({'broker': broker_name, 'symbol': symbol, 'qty': sell_qty, 'side': 'sell', 'price': price, 'reason': reason, 'timestamp': datetime.now().isoformat(), **result})
                key = f"{broker_name}:{symbol}"
                if key in self.positions:
                    del self.positions[key]
                logger.info(f"SELL EXECUTED ({reason}): {sell_qty} {symbol} @ ${price:.2f}")
        except Exception as e:
            logger.error(f"Execute sell error: {e}")
    
    def submit_order(self, broker_name, symbol, qty, side, order_type='market', **kwargs):
        broker = self.balance_aggregator.brokers.get(broker_name)
        if not broker:
            return {'success': False, 'error': f'Broker {broker_name} not found'}
        if not broker.connected:
            return {'success': False, 'error': f'Broker {broker_name} not connected - check API keys'}
        result = broker.submit_order(symbol, qty, side, order_type, **kwargs)
        if result.get('success'):
            self.total_trades += 1
            self.orders.append({'broker': broker_name, 'symbol': symbol, 'qty': qty, 'side': side, 'timestamp': datetime.now().isoformat(), **result})
        return result
    
    def get_orders(self, broker_name=None):
        if broker_name:
            broker = self.balance_aggregator.brokers.get(broker_name)
            if broker:
                return broker.get_orders()
            return []
        # Return internally tracked orders (includes all brokers + our execution metadata)
        return list(reversed(self.orders[-200:]))
    
    def close_position(self, broker_name, symbol):
        broker = self.balance_aggregator.brokers.get(broker_name)
        if not broker:
            return {'success': False, 'error': 'Broker not found'}
        return broker.close_position(symbol)


# ============ STRATEGIES ============
STRATEGIES = {
    'scalping': {
        'name': 'Scalping',
        'icon': '⚡',
        'risk': 'High',
        'timeframe': '1-5 min',
        'indicators': 'EMA 9/21, RSI, Volume',
        'stop_loss': '0.5%',
        'take_profit': '1%',
        'description': 'High-frequency trading capturing small price movements',
        'allocation': 10
    },
    'day_trading': {
        'name': 'Day Trading',
        'icon': '☀️',
        'risk': 'Medium',
        'timeframe': '5-15 min',
        'indicators': 'VWAP, Bollinger Bands, RSI',
        'stop_loss': '1.5%',
        'take_profit': '3%',
        'description': 'Intraday trades closed before market close',
        'allocation': 20
    },
    'swing_trading': {
        'name': 'Swing Trading',
        'icon': '📈',
        'risk': 'Medium',
        'timeframe': '1-5 days',
        'indicators': 'MACD, SMA 20/50, Volume',
        'stop_loss': '4%',
        'take_profit': '8%',
        'description': 'Multi-day holds capturing medium-term trends',
        'allocation': 30
    },
    'momentum': {
        'name': 'Momentum',
        'icon': '🚀',
        'risk': 'High',
        'timeframe': 'Daily',
        'indicators': 'ROC, Volume, RSI',
        'stop_loss': '6%',
        'take_profit': '12%',
        'description': 'Ride strong price trends with volume confirmation',
        'allocation': 15
    },
    'mean_reversion': {
        'name': 'Mean Reversion',
        'icon': '🔄',
        'risk': 'Medium',
        'timeframe': 'Daily',
        'indicators': 'Bollinger Bands, RSI, Z-Score',
        'stop_loss': '3%',
        'take_profit': '5%',
        'description': 'Trade price reversions to the mean',
        'allocation': 15
    },
    'breakout': {
        'name': 'Breakout',
        'icon': '💥',
        'risk': 'High',
        'timeframe': 'Daily',
        'indicators': '20-day H/L, ATR, Volume',
        'stop_loss': '5%',
        'take_profit': '15%',
        'description': 'Trade breakouts from consolidation patterns',
        'allocation': 10
    }
}


# ============ TOUCH KEYBOARD HTML ============
KEYBOARD_HTML = """
<style>
#omni-keyboard {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: linear-gradient(180deg, #1a1a2e 0%, #0a0a0f 100%);
  border-top: 2px solid #333;
  padding: 8px;
  z-index: 99999;
  display: none;
  user-select: none;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.5);
}
.omni-kb-row { display: flex; justify-content: center; gap: 4px; margin-bottom: 4px; }
.omni-kb-btn {
  flex: 1; max-width: 70px; height: 48px;
  background: linear-gradient(180deg, #444 0%, #333 100%);
  color: #fff; border: 1px solid #555;
  border-radius: 6px; font-size: 18px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.1s;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}
.omni-kb-btn:hover { background: linear-gradient(180deg, #555 0%, #444 100%); }
.omni-kb-btn:active { background: #00d4ff; color: #000; transform: scale(0.95); }
.omni-kb-btn.wide { flex: 2; max-width: 110px; }
.omni-kb-btn.space { flex: 4; max-width: 280px; }
.omni-kb-btn.special { background: linear-gradient(180deg, #6366f1 0%, #4f46e5 100%); }
</style>
<div id="omni-keyboard">
  <div class="omni-kb-row">
    <div class="omni-kb-btn" data-k="1">1</div><div class="omni-kb-btn" data-k="2">2</div><div class="omni-kb-btn" data-k="3">3</div>
    <div class="omni-kb-btn" data-k="4">4</div><div class="omni-kb-btn" data-k="5">5</div><div class="omni-kb-btn" data-k="6">6</div>
    <div class="omni-kb-btn" data-k="7">7</div><div class="omni-kb-btn" data-k="8">8</div><div class="omni-kb-btn" data-k="9">9</div>
    <div class="omni-kb-btn" data-k="0">0</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn" data-k="q">q</div><div class="omni-kb-btn" data-k="w">w</div><div class="omni-kb-btn" data-k="e">e</div>
    <div class="omni-kb-btn" data-k="r">r</div><div class="omni-kb-btn" data-k="t">t</div><div class="omni-kb-btn" data-k="y">y</div>
    <div class="omni-kb-btn" data-k="u">u</div><div class="omni-kb-btn" data-k="i">i</div><div class="omni-kb-btn" data-k="o">o</div>
    <div class="omni-kb-btn" data-k="p">p</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn" data-k="a">a</div><div class="omni-kb-btn" data-k="s">s</div><div class="omni-kb-btn" data-k="d">d</div>
    <div class="omni-kb-btn" data-k="f">f</div><div class="omni-kb-btn" data-k="g">g</div><div class="omni-kb-btn" data-k="h">h</div>
    <div class="omni-kb-btn" data-k="j">j</div><div class="omni-kb-btn" data-k="k">k</div><div class="omni-kb-btn" data-k="l">l</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn wide special" data-k="shift">&#8679;</div>
    <div class="omni-kb-btn" data-k="z">z</div><div class="omni-kb-btn" data-k="x">x</div>
    <div class="omni-kb-btn" data-k="c">c</div><div class="omni-kb-btn" data-k="v">v</div>
    <div class="omni-kb-btn" data-k="b">b</div><div class="omni-kb-btn" data-k="n">n</div>
    <div class="omni-kb-btn" data-k="m">m</div>
    <div class="omni-kb-btn wide special" data-k="bksp">&#9003;</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn wide special" data-k="toggle">123</div>
    <div class="omni-kb-btn space" data-k=" ">Space</div>
    <div class="omni-kb-btn wide special" data-k="enter">&#9166;</div>
  </div>
</div>
<script>
(function() {
  let kb = document.getElementById('omni-keyboard');
  let activeInput = null;
  let shifted = false;
  let symMode = false;
  const letters = "abcdefghijklmnopqrstuvwxyz";
  const syms1 = "1234567890";
  const syms2 = "!@#$%^&*()";
  
  function updateLabels() {
    document.querySelectorAll('.omni-kb-btn[data-k]').forEach(btn => {
      let k = btn.getAttribute('data-k');
      if (k.length === 1 && letters.includes(k)) {
        btn.textContent = shifted ? k.toUpperCase() : k.toLowerCase();
      }
    });
  }
  
  function insertChar(ch) {
    if (!activeInput) return;
    let start = activeInput.selectionStart;
    let end = activeInput.selectionEnd;
    let val = activeInput.value;
    activeInput.value = val.substring(0, start) + ch + val.substring(end);
    activeInput.selectionStart = activeInput.selectionEnd = start + ch.length;
    activeInput.dispatchEvent(new Event('input', {bubbles:true}));
  }
  
  kb.addEventListener('click', function(e) {
    let btn = e.target.closest('.omni-kb-btn');
    if (!btn) return;
    let k = btn.getAttribute('data-k');
    if (!k) return;
    
    if (k === 'shift') { shifted = !shifted; updateLabels(); return; }
    if (k === 'bksp') {
      if (activeInput) {
        let start = activeInput.selectionStart;
        let end = activeInput.selectionEnd;
        let val = activeInput.value;
        if (start === end && start > 0) {
          activeInput.value = val.substring(0, start-1) + val.substring(end);
          activeInput.selectionStart = activeInput.selectionEnd = start - 1;
        } else {
          activeInput.value = val.substring(0, start) + val.substring(end);
          activeInput.selectionStart = activeInput.selectionEnd = start;
        }
        activeInput.dispatchEvent(new Event('input', {bubbles:true}));
      }
      return;
    }
    if (k === 'enter') {
      kb.style.display = 'none';
      if (activeInput) activeInput.blur();
      return;
    }
    if (k === 'toggle') {
      symMode = !symMode;
      document.querySelectorAll('.omni-kb-row:first-child .omni-kb-btn').forEach((btn, i) => {
        if (syms1[i]) {
          btn.setAttribute('data-k', symMode ? syms2[i] : syms1[i]);
          btn.textContent = symMode ? syms2[i] : syms1[i];
        }
      });
      btn.textContent = symMode ? "abc" : "123";
      return;
    }
    
    let ch = k;
    if (k.length === 1 && letters.includes(k)) {
      ch = shifted ? k.toUpperCase() : k.toLowerCase();
    }
    insertChar(ch);
    if (shifted) { shifted = false; updateLabels(); }
  });
  
  function showKeyboard(el) {
    activeInput = el;
    kb.style.display = 'block';
    el.scrollIntoView({behavior: 'smooth', block: 'center'});
  }
  
  function hideKeyboard() {
    kb.style.display = 'none';
    activeInput = null;
  }
  
  document.querySelectorAll('input, textarea').forEach(el => {
    el.addEventListener('focus', () => showKeyboard(el));
  });
  
  document.addEventListener('click', e => {
    if (e.target.matches('input, textarea')) return;
    if (e.target.closest('#omni-keyboard')) return;
    hideKeyboard();
  });
})();
</script>
"""


# In-memory log buffer for /api/logs
class LogBufferHandler(logging.Handler):
    def __init__(self, capacity=500):
        super().__init__()
        self.capacity = capacity
        self.buffer = []
    def emit(self, record):
        msg = self.format(record)
        self.buffer.append({'time': datetime.fromtimestamp(record.created).isoformat(), 'level': record.levelname.lower(), 'message': msg})
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

log_buffer = LogBufferHandler(capacity=500)
log_buffer.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
logging.getLogger().addHandler(log_buffer)

# ============ FLASK APP ============
app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)
app.secret_key = os.environ.get('SECRET_KEY', 'omnibot-titan-secret-key-2024')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
settings = Settings()
balance_aggregator = BalanceAggregator()

# Initialize brokers with settings
def init_brokers():
    global alpaca, binance, paypal
    
    alpaca_config = settings.get_broker_config('alpaca')
    alpaca = AlpacaBroker(
        api_key=alpaca_config.get('api_key'),
        secret_key=alpaca_config.get('secret_key'),
        paper=alpaca_config.get('paper', True)
    )
    
    binance_config = settings.get_broker_config('binance')
    binance = BinanceBroker(
        api_key=binance_config.get('api_key'),
        secret_key=binance_config.get('secret_key'),
        testnet=binance_config.get('testnet', True)
    )
    
    paypal_config = settings.get_broker_config('paypal')
    paypal = PayPalWallet(
        client_id=paypal_config.get('client_id'),
        client_secret=paypal_config.get('client_secret'),
        sandbox=paypal_config.get('sandbox', True)
    )
    
    if alpaca_config.get('enabled') and alpaca.api_key:
        alpaca.connect()
    if binance_config.get('enabled') and binance.api_key:
        binance.connect()
    if paypal_config.get('enabled'):
        paypal.connect()
    
    balance_aggregator.add_broker('alpaca', alpaca)
    balance_aggregator.add_broker('binance', binance)
    balance_aggregator.add_broker('paypal', paypal)
    
    logger.info(f"Brokers initialized: Alpaca={alpaca.connected}, Binance={binance.connected}, PayPal={paypal.connected}")

init_brokers()
engine = TradingEngine(balance_aggregator, settings)


@app.after_request
def inject_touch_keyboard(response):
    if response.content_type == 'text/html; charset=utf-8':
        try:
            text = response.get_data(as_text=True)
            if text and 'id="omni-keyboard"' not in text:
                if '</body>' in text:
                    text = text.replace('</body>', KEYBOARD_HTML + '</body>')
                else:
                    text = text + KEYBOARD_HTML
                response.set_data(text)
        except Exception:
            pass
    return response


# ============ ROUTES ============
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or request.form
        if data.get('username') == 'admin' and data.get('password') == 'admin':
            session['logged_in'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid credentials'})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/positions')
def positions():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('positions.html')

@app.route('/orders')
def orders():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('orders.html')

@app.route('/graphs')
def graphs():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('graphs.html')

@app.route('/strategy')
def strategy():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('strategy.html')

@app.route('/scan')
def scan_page():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('scan.html')

@app.route('/settings')
def settings_page():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('settings.html')

@app.route('/logs')
def logs():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('logs.html')

@app.route('/trade')
def trade_page():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('trade.html')


# ============ API ROUTES ============
@app.route('/api/status')
def api_status():
    balances = balance_aggregator.get_all_balances()
    total_value = balance_aggregator.get_total_balance()
    breakdown = balance_aggregator.get_portfolio_breakdown()
    
    return jsonify({
        'portfolio': {
            'total_value': total_value,
            'daily_pnl': engine.daily_pnl,
            'balances': balances,
            'breakdown': breakdown
        },
        'tracked_positions': balance_aggregator.get_all_positions(),
        'trading_engine': engine.get_status(),
        'brokers': {
            'alpaca': {'connected': alpaca.connected, 'paper': alpaca.paper},
            'binance': {'connected': binance.connected, 'testnet': binance.testnet},
            'paypal': {'connected': paypal.connected}
        }
    })

@app.route('/api/debug_balance')
def api_debug_balance():
    """Diagnostic endpoint: show exactly what each broker returns."""
    result = {}
    for name, broker in balance_aggregator.brokers.items():
        try:
            bal = broker.get_balance()
            is_testnet = False
            if name == 'binance':
                is_testnet = getattr(broker, 'testnet', False)
            if name == 'paypal':
                is_testnet = getattr(broker, 'sandbox', False)
            if name == 'alpaca':
                is_testnet = getattr(broker, 'paper', True)
            result[name] = {
                'connected': broker.connected,
                'is_testnet_or_paper': is_testnet,
                'raw_balance': bal,
                'contribution_to_total': 0
            }
            if isinstance(bal, dict):
                if name == 'alpaca':
                    result[name]['contribution_to_total'] = bal.get('portfolio_value', 0)
                elif name == 'binance':
                    raw_sum = sum(v for v in bal.values() if isinstance(v, (int, float)))
                    result[name]['raw_sum'] = raw_sum
                    if is_testnet:
                        result[name]['usd_valuation'] = 'skipped_testnet'
                        result[name]['contribution_to_total'] = 0
                    else:
                        usd_val = balance_aggregator._value_binance_usd(broker, bal) if broker.connected else 0
                        result[name]['usd_valuation'] = usd_val
                        result[name]['contribution_to_total'] = usd_val
                elif name == 'paypal':
                    result[name]['contribution_to_total'] = bal.get('usd', 0)
        except Exception as e:
            result[name] = {'error': str(e)}
    result['computed_total'] = balance_aggregator.get_total_balance()
    return jsonify(result)

@app.route('/api/positions')
def api_positions():
    positions = balance_aggregator.get_all_positions()
    return jsonify({
        'tracked_positions': positions,
        'broker_positions': {}
    })

@app.route('/api/orders')
def api_orders():
    broker = request.args.get('broker')
    orders = engine.get_orders(broker)
    return jsonify({'orders': orders})

@app.route('/api/strategies')
def api_strategies():
    return jsonify({
        'current_strategy': settings.get('active_strategy', 'swing_trading'),
        'strategies': STRATEGIES
    })

@app.route('/api/trading/strategy', methods=['POST'])
def set_strategy():
    req = request.get_json()
    strategy = req.get('strategy', 'swing_trading')
    settings.set('active_strategy', strategy)
    return jsonify({'success': True, 'strategy': strategy})

@app.route('/api/trading/start', methods=['POST'])
def start_trading():
    engine.start()
    settings.set('trading_enabled', True)
    return jsonify({'success': True})

@app.route('/api/trading/stop', methods=['POST'])
def stop_trading():
    engine.stop()
    settings.set('trading_enabled', False)
    return jsonify({'success': True})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        data = request.get_json()
        
        if 'brokers' in data:
            for broker_name, broker_config in data['brokers'].items():
                settings.update_broker_config(broker_name, broker_config)
                balance_aggregator.reconnect_broker(broker_name, settings)
        
        for k, v in data.items():
            if k != 'brokers':
                settings.set(k, v)
        
        return jsonify({'success': True})
    
    return jsonify(settings.get_all())

@app.route('/api/charts/data')
def api_charts():
    return jsonify({
        'total_return': 0,
        'win_rate': engine.get_status().get('win_rate', 0),
        'portfolio': {'labels': [], 'values': []},
        'allocation': {'labels': ['Cash'], 'values': [100]},
        'pnl': {'labels': [], 'values': []},
        'win_loss': {'wins': engine.winning_trades, 'losses': engine.total_trades - engine.winning_trades}
    })


@app.route('/api/logs')
def api_logs():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    return jsonify({'logs': log_buffer.buffer[-200:]})

@app.route('/api/scan')
def api_scan():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    return jsonify({
        'scan_log': engine.scan_log[-50:],
        'running': engine.running,
        'total_trades': engine.total_trades,
        'watchlist': engine._get_watchlist()
    })

@app.route('/api/trading/sell_all', methods=['POST'])
def sell_all():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    results = []
    for name, broker in balance_aggregator.brokers.items():
        try:
            positions = broker.get_positions()
            for pos in positions:
                symbol = pos.get('symbol')
                qty = pos.get('qty', 0)
                if qty > 0:
                    r = broker.submit_order(symbol, qty, 'sell')
                    results.append({'broker': name, 'symbol': symbol, 'result': r})
        except Exception as e:
            results.append({'broker': name, 'error': str(e)})
    return jsonify({'success': True, 'results': results})

# ============ ORDER EXECUTION API ============
@app.route('/api/order/submit', methods=['POST'])
def submit_order():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    data = request.get_json()
    broker = data.get('broker', 'alpaca')
    symbol = data.get('symbol', '').upper()
    qty = float(data.get('qty', 0))
    side = data.get('side', 'buy')
    order_type = data.get('type', 'market')
    
    if not symbol or qty <= 0:
        return jsonify({'success': False, 'error': 'Invalid symbol or quantity'})
    
    result = engine.submit_order(broker, symbol, qty, side, order_type)
    return jsonify(result)

@app.route('/api/order/cancel', methods=['POST'])
def cancel_order():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    data = request.get_json()
    broker = data.get('broker', 'alpaca')
    order_id = data.get('order_id')
    
    broker_obj = balance_aggregator.brokers.get(broker)
    if not broker_obj:
        return jsonify({'success': False, 'error': 'Broker not found'})
    
    result = broker_obj.cancel_order(order_id)
    return jsonify(result)

@app.route('/api/position/close', methods=['POST'])
def close_position():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    data = request.get_json()
    broker = data.get('broker', 'alpaca')
    symbol = data.get('symbol')
    
    result = engine.close_position(broker, symbol)
    return jsonify(result)


# ============ WEBSOCKET EVENTS ============
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('status', engine.get_status())

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')


# ============ MAIN ============
def main():
    host = settings.get('dashboard_host', '0.0.0.0')
    port = settings.get('dashboard_port', 8081)
    
    logger.info("=" * 50)
    logger.info("  OMNIBOT TITAN v2.7.2")
    logger.info("  Professional Trading Bot")
    logger.info("=" * 50)
    logger.info(f"Dashboard: http://{host}:{port}")
    logger.info(f"Brokers: Alpaca={alpaca.connected}, Binance={binance.connected}, PayPal={paypal.connected}")
    
    socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
