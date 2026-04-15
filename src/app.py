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
from flask import Flask, render_template, jsonify, request, session, redirect
from flask_socketio import SocketIO

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
            'active_strategy': 'swing_trading',
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
    
    def submit_order(self, symbol, qty, side, order_type='market'):
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            side_enum = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
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
    
    def submit_order(self, symbol, qty, side, order_type='MARKET'):
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        try:
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"
            
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
        total = 0
        for name, broker in self.brokers.items():
            try:
                bal = broker.get_balance()
                if isinstance(bal, dict):
                    total += sum(v for v in bal.values() if isinstance(v, (int, float)))
            except Exception as e:
                logger.error(f"Balance error for {name}: {e}")
        return total
    
    def get_all_balances(self):
        result = {}
        for name, broker in self.brokers.items():
            try:
                result[name] = broker.get_balance()
            except Exception as e:
                logger.error(f"Balance error for {name}: {e}")
                result[name] = {}
        return result
    
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
    """Main trading engine"""
    
    def __init__(self, balance_aggregator, settings):
        self.balance_aggregator = balance_aggregator
        self.settings = settings
        self.running = False
        self.thread = None
        self.daily_pnl = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.positions = {}
        self.orders = []
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._trading_loop, daemon=True)
            self.thread.start()
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
    
    def _trading_loop(self):
        while self.running:
            try:
                time.sleep(5)
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(5)
    
    def submit_order(self, broker_name, symbol, qty, side, order_type='market', **kwargs):
        broker = self.balance_aggregator.brokers.get(broker_name)
        if not broker:
            return {'success': False, 'error': f'Broker {broker_name} not found'}
        
        if not broker.connected:
            return {'success': False, 'error': f'Broker {broker_name} not connected - check API keys'}
        
        result = broker.submit_order(symbol, qty, side, order_type, **kwargs)
        
        if result.get('success'):
            self.total_trades += 1
            self.orders.append({
                'broker': broker_name,
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'timestamp': datetime.now().isoformat(),
                **result
            })
        
        return result
    
    def get_orders(self, broker_name=None):
        if broker_name:
            broker = self.balance_aggregator.brokers.get(broker_name)
            if broker:
                return broker.get_orders()
            return []
        
        all_orders = []
        for name, broker in self.balance_aggregator.brokers.items():
            try:
                orders = broker.get_orders()
                for o in orders:
                    o['broker'] = name
                    all_orders.append(o)
            except:
                pass
        return all_orders
    
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
    
    return jsonify({
        'portfolio': {
            'total_value': total_value,
            'daily_pnl': engine.daily_pnl,
            'balances': balances
        },
        'tracked_positions': balance_aggregator.get_all_positions(),
        'trading_engine': engine.get_status(),
        'brokers': {
            'alpaca': {'connected': alpaca.connected, 'paper': alpaca.paper},
            'binance': {'connected': binance.connected, 'testnet': binance.testnet},
            'paypal': {'connected': paypal.connected}
        }
    })

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
