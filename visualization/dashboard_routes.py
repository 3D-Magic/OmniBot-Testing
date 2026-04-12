"""
Dashboard Routes
Flask Blueprint for dashboard endpoints
"""

from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from functools import wraps

# Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Global references (set by init_dashboard)
_settings = None
_balance_aggregator = None
_wifi_manager = None


def init_dashboard(settings, balance_aggregator, wifi_manager):
    """Initialize dashboard with required components"""
    global _settings, _balance_aggregator, _wifi_manager
    _settings = settings
    _balance_aggregator = balance_aggregator
    _wifi_manager = wifi_manager


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    return render_template('index.html')


@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if _settings.verify_password(password):
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard.index'))
        
        return render_template('login.html', error='Invalid password')
    
    return render_template('login.html')


@dashboard_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('dashboard.login'))


@dashboard_bp.route('/settings')
@login_required
def settings_page():
    """Settings page"""
    return render_template('settings.html')


@dashboard_bp.route('/api/auth/check')
def api_auth_check():
    """Check if user is authenticated"""
    return jsonify({
        'authenticated': session.get('logged_in', False)
    })


@dashboard_bp.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """API login endpoint (for AJAX requests)"""
    data = request.json or {}
    password = data.get('password', '')
    
    if _settings.verify_password(password):
        session['logged_in'] = True
        session.permanent = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid password'}), 401


# ==================== API ENDPOINTS ====================

@dashboard_bp.route('/api/dashboard_data')
@login_required
def dashboard_data():
    """Get all dashboard data in one call"""
    if _balance_aggregator is None:
        return jsonify({'error': 'Balance aggregator not initialized'}), 500
    
    mode = _settings.get('trading_mode', 'demo')
    
    # Get real balances from brokers (don't use demo override)
    # Only use demo if NO brokers are configured
    balances = _balance_aggregator.get_all_balances(demo_mode=False)
    
    # If no real data available, fall back to demo
    if balances.get('total_capital', 0) == 0 and len(balances.get('broker_data', {})) == 0:
        balances = _balance_aggregator.get_all_balances(demo_mode=True)
    
    return jsonify({
        'total_capital': balances.get('total_capital', 0),
        'stocks': balances.get('stocks', 0),
        'crypto': balances.get('crypto', 0),
        'forex': balances.get('forex', 0),
        'broker_data': balances.get('broker_data', {}),
        'mode': mode,
        'is_demo': mode == 'demo',
        'last_update': balances.get('last_update')
    })


@dashboard_bp.route('/api/portfolio')
@login_required
def api_portfolio():
    """Get portfolio data"""
    return dashboard_data()


@dashboard_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    """Get or update settings"""
    if request.method == 'GET':
        return jsonify(_settings.get_safe())
    
    # POST - Update settings
    data = request.json or {}
    
    # Update allowed fields
    allowed_fields = [
        'alpaca_key', 'alpaca_secret', 'binance_key', 'binance_secret',
        'ig_api_key', 'ig_username', 'ig_password', 'ig_account_id',
        'ibkr_account_id', 'ibkr_username', 'ibkr_password',
        'trading_mode', 'strategy', 'trading_enabled', 'high_frequency'
    ]
    
    for field in allowed_fields:
        if field in data:
            _settings.set(field, data[field])
    
    return jsonify({'success': True})


@dashboard_bp.route('/api/broker_status')
@login_required
def api_broker_status():
    """Get broker connection status"""
    if _balance_aggregator is None:
        return jsonify({'error': 'Not initialized'}), 500
    
    return jsonify(_balance_aggregator.get_broker_status())


@dashboard_bp.route('/api/wifi/scan')
@login_required
def api_wifi_scan():
    """Scan for WiFi networks"""
    if _wifi_manager is None:
        return jsonify({'networks': [], 'error': 'WiFi manager not initialized'})
    
    networks = _wifi_manager.scan_networks()
    return jsonify({'networks': networks})


@dashboard_bp.route('/api/wifi/status')
@login_required
def api_wifi_status():
    """Get WiFi status"""
    if _wifi_manager is None:
        return jsonify({'connected': False, 'error': 'WiFi manager not initialized'})
    
    return jsonify(_wifi_manager.get_status())


@dashboard_bp.route('/api/wifi/connect', methods=['POST'])
@login_required
def api_wifi_connect():
    """Connect to WiFi network"""
    if _wifi_manager is None:
        return jsonify({'success': False, 'error': 'WiFi manager not initialized'})
    
    data = request.json or {}
    result = _wifi_manager.connect(
        ssid=data.get('ssid'),
        password=data.get('password', '')
    )
    return jsonify(result)


@dashboard_bp.route('/api/system/info')
@login_required
def api_system_info():
    """Get system information"""
    import subprocess
    import os
    
    try:
        # Get IP
        ip_result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        ip = ip_result.stdout.strip().split()[0] if ip_result.stdout else 'Unknown'
        
        # Get uptime
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                uptime_hours = int(uptime_seconds / 3600)
        except:
            uptime_hours = 0
        
        # Get CPU temp (Raspberry Pi)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = round(int(f.read().strip()) / 1000, 1)
        except:
            temp = None
        
        return jsonify({
            'ip': ip,
            'uptime_hours': uptime_hours,
            'temperature': temp,
            'version': _settings.get('version', 'v2.7.2-titan'),
            'wifi': _wifi_manager.get_status() if _wifi_manager else None
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@dashboard_bp.route('/api/trading/start', methods=['POST'])
@login_required
def api_trading_start():
    """Start trading"""
    _settings.set('trading_enabled', True)
    return jsonify({'success': True, 'status': 'started'})


@dashboard_bp.route('/api/trading/stop', methods=['POST'])
@login_required
def api_trading_stop():
    """Stop trading"""
    _settings.set('trading_enabled', False)
    return jsonify({'success': True, 'status': 'stopped'})


@dashboard_bp.route('/api/trading/status')
@login_required
def api_trading_status():
    """Get trading status"""
    return jsonify({
        'enabled': _settings.get('trading_enabled', False),
        'mode': _settings.get('trading_mode', 'demo'),
        'strategy': _settings.get('strategy', 'moderate')
    })


@dashboard_bp.route('/api/market/status')
@login_required
def api_market_status():
    """Get market open/closed status"""
    from datetime import datetime
    try:
        ny_time = datetime.now()
        is_weekday = ny_time.weekday() < 5
        hour = ny_time.hour
        minute = ny_time.minute
        time_in_minutes = hour * 60 + minute
        nyse_open = (9 * 60 + 30) <= time_in_minutes <= (16 * 60)
        
        return jsonify({
            'nyse': {'open': is_weekday and nyse_open, 'hours': '9:30 AM - 4:00 PM ET'},
            'nasdaq': {'open': is_weekday and nyse_open, 'hours': '9:30 AM - 4:00 PM ET'},
            'forex': {'open': True, 'hours': 'Sun 5PM - Fri 5PM ET'},
            'crypto': {'open': True, 'hours': '24/7'}
        })
    except:
        return jsonify({
            'nyse': {'open': True, 'hours': '9:30 AM - 4:00 PM ET'},
            'nasdaq': {'open': True, 'hours': '9:30 AM - 4:00 PM ET'},
            'forex': {'open': True, 'hours': '24/5'},
            'crypto': {'open': True, 'hours': '24/7'}
        })


@dashboard_bp.route('/api/trading/positions')
@login_required
def api_trading_positions():
    """Get current trading positions"""
    from flask import current_app
    engine = current_app.trading_engine if hasattr(current_app, 'trading_engine') else None
    
    if engine:
        return jsonify({
            'positions': engine.get_positions_summary(),
            'count': len(engine.positions)
        })
    return jsonify({'positions': [], 'count': 0})


@dashboard_bp.route('/api/trading/orders')
@login_required
def api_trading_orders():
    """Get recent orders"""
    from flask import current_app
    engine = current_app.trading_engine if hasattr(current_app, 'trading_engine') else None
    
    if engine:
        # Return last 20 orders, most recent first
        orders = sorted(engine.orders, key=lambda x: x['timestamp'], reverse=True)[:20]
        return jsonify({'orders': orders, 'count': len(orders)})
    return jsonify({'orders': [], 'count': 0})


@dashboard_bp.route('/api/trading/engine_status')
@login_required
def api_trading_engine_status():
    """Get detailed trading engine status"""
    from flask import current_app
    engine = current_app.trading_engine if hasattr(current_app, 'trading_engine') else None
    
    if engine:
        return jsonify(engine.get_status())
    return jsonify({
        'running': False,
        'mode': _settings.get('trading_mode', 'demo'),
        'strategy': _settings.get('strategy', 'moderate'),
        'trading_enabled': _settings.get('trading_enabled', False)
    })
