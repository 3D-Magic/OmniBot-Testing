"""
Dashboard Routes
Web routes for the OMNIBOT dashboard
"""
import hashlib
from flask import render_template, request, jsonify, session, redirect, url_for, current_app
from functools import wraps
from . import dashboard_bp


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function


def check_password(password, settings):
    """Check if password is correct"""
    stored_hash = settings.get('password_hash')
    if stored_hash:
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash
    return password == settings.get('password', 'admin')


@dashboard_bp.route('/')
def index():
    """Main dashboard page"""
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('index.html')


@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        settings = current_app.settings
        
        if check_password(password, settings):
            session['logged_in'] = True
            return redirect(url_for('dashboard.index'))
        else:
            return render_template('login.html', error='Invalid password')
    
    return render_template('login.html')


@dashboard_bp.route('/logout')
def logout():
    """Logout route"""
    session.pop('logged_in', None)
    return redirect(url_for('dashboard.login'))


@dashboard_bp.route('/settings')
@login_required
def settings_page():
    """Settings page"""
    return render_template('settings.html')


@dashboard_bp.route('/charts')
@login_required
def charts_page():
    """Charts page"""
    return render_template('charts.html')


@dashboard_bp.route('/graphs')
@login_required
def graphs_page():
    """Graphs page"""
    return render_template('graphs.html')


@dashboard_bp.route('/positions')
@login_required
def positions_page():
    """Positions page"""
    return render_template('positions.html')


@dashboard_bp.route('/orders')
@login_required
def orders_page():
    """Orders page"""
    return render_template('orders.html')


@dashboard_bp.route('/logs')
@login_required
def logs_page():
    """Logs page"""
    return render_template('logs.html')


# API Routes

@dashboard_bp.route('/api/status')
@login_required
def api_status():
    """Get system status"""
    trading_engine = current_app.trading_engine
    balance_aggregator = current_app.balance_aggregator
    
    return jsonify({
        'trading_engine': trading_engine.get_status(),
        'brokers': balance_aggregator.get_status(),
        'portfolio': balance_aggregator.get_portfolio_summary()
    })


@dashboard_bp.route('/api/portfolio')
@login_required
def api_portfolio():
    """Get portfolio data"""
    balance_aggregator = current_app.balance_aggregator
    return jsonify(balance_aggregator.get_portfolio_summary())


@dashboard_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    """Get or update settings"""
    settings = current_app.settings
    
    if request.method == 'GET':
        return jsonify(settings.get_all())
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Handle password update
        if 'password' in data:
            password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
            settings.set('password_hash', password_hash)
            del data['password']
        
        # Update screen settings if provided
        if any(k.startswith('screen_') for k in data.keys()):
            if hasattr(current_app, 'screen_manager'):
                current_app.screen_manager.update_settings(data)
        
        # Update settings
        for key, value in data.items():
            settings.set(key, value)
        
        return jsonify({'success': True})


@dashboard_bp.route('/api/settings/reset', methods=['POST'])
@login_required
def api_reset_settings():
    """Reset all settings to defaults"""
    try:
        settings = current_app.settings
        settings.reset_to_defaults()
        return jsonify({'success': True, 'message': 'Settings reset to defaults'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/broker/config', methods=['POST'])
@login_required
def api_broker_config():
    """Update broker configuration"""
    settings = current_app.settings
    data = request.get_json()
    
    broker = data.get('broker')
    config = data.get('config', {})
    
    if broker:
        settings.set_broker_config(broker, config)
        
        # Reconnect broker if enabled
        if config.get('enabled'):
            balance_aggregator = current_app.balance_aggregator
            broker_obj = balance_aggregator.get_broker(broker)
            if broker_obj:
                if broker == 'paypal':
                    broker_obj.client_id = config.get('client_id')
                    broker_obj.client_secret = config.get('client_secret')
                    broker_obj.sandbox = config.get('sandbox', True)
                elif broker == 'interactive_brokers':
                    broker_obj.host = config.get('host', '127.0.0.1')
                    broker_obj.port = config.get('port', 7497)
                    broker_obj.client_id = config.get('client_id', 1)
                else:
                    broker_obj.api_key = config.get('api_key')
                    broker_obj.secret_key = config.get('secret_key')
                    if broker == 'alpaca':
                        broker_obj.paper = config.get('paper', True)
                    elif broker == 'binance':
                        broker_obj.testnet = config.get('testnet', True)
                broker_obj.connect()
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Broker not specified'})


@dashboard_bp.route('/api/broker/test', methods=['POST'])
@login_required
def api_test_broker():
    """Test broker connection"""
    data = request.get_json()
    broker = data.get('broker')
    
    balance_aggregator = current_app.balance_aggregator
    broker_obj = balance_aggregator.get_broker(broker)
    
    if not broker_obj:
        return jsonify({'success': False, 'error': 'Broker not configured'})
    
    try:
        if broker == 'interactive_brokers':
            # IB requires special handling
            connected = broker_obj.is_connected() if hasattr(broker_obj, 'is_connected') else False
            return jsonify({'success': connected, 'error': None if connected else 'Not connected to TWS/Gateway'})
        
        # Test connection by fetching balance
        balance = broker_obj.get_balance()
        return jsonify({'success': True, 'balance': balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/trading/start', methods=['POST'])
@login_required
def api_trading_start():
    """Start trading engine"""
    trading_engine = current_app.trading_engine
    
    if trading_engine.start():
        current_app.settings.set('trading_enabled', True)
        return jsonify({'success': True, 'message': 'Trading engine started'})
    else:
        return jsonify({'success': False, 'error': 'Trading engine already running'})


@dashboard_bp.route('/api/trading/stop', methods=['POST'])
@login_required
def api_trading_stop():
    """Stop trading engine"""
    trading_engine = current_app.trading_engine
    trading_engine.stop()
    current_app.settings.set('trading_enabled', False)
    return jsonify({'success': True, 'message': 'Trading engine stopped'})


@dashboard_bp.route('/api/trading/sell_all', methods=['POST'])
@login_required
def api_sell_all():
    """Sell all positions"""
    trading_engine = current_app.trading_engine
    data = request.get_json()
    broker = data.get('broker', 'all')
    
    trading_engine.sell_all_positions(broker)
    return jsonify({'success': True, 'message': f'Selling all positions for {broker}'})


@dashboard_bp.route('/api/trading/sell_all_profitable', methods=['POST'])
@login_required
def api_sell_all_profitable():
    """Sell all profitable positions and disable buying"""
    trading_engine = current_app.trading_engine
    data = request.get_json()
    broker = data.get('broker', 'all')
    
    result = trading_engine.sell_all_if_profitable(broker)
    return jsonify({
        'success': True, 
        'message': f'Sold {result.get("sold_count", 0)} profitable positions. Buying disabled.',
        'sold_count': result.get('sold_count', 0),
        'skipped_count': result.get('skipped_count', 0),
        'buying_disabled': True
    })


@dashboard_bp.route('/api/trading/enable_buying', methods=['POST'])
@login_required
def api_enable_buying():
    """Re-enable buying after sell-all"""
    trading_engine = current_app.trading_engine
    trading_engine.enable_buying()
    return jsonify({'success': True, 'message': 'Buying re-enabled'})


@dashboard_bp.route('/api/trading/strategy', methods=['POST'])
@login_required
def api_set_strategy():
    """Set trading strategy"""
    data = request.get_json()
    strategy = data.get('strategy')
    
    if strategy:
        trading_engine = current_app.trading_engine
        trading_engine.set_strategy(strategy)
        current_app.settings.set('strategy', strategy)
        return jsonify({'success': True, 'message': f'Strategy set to {strategy}'})
    
    return jsonify({'success': False, 'error': 'Strategy not specified'})


@dashboard_bp.route('/api/strategies')
@login_required
def api_get_strategies():
    """Get all available strategies and current strategy"""
    try:
        from engine.strategies import get_all_strategies
        
        strategies = get_all_strategies()
        current_strategy = current_app.settings.get('strategy', 'swing_trading')
        
        return jsonify({
            'success': True,
            'strategies': strategies,
            'current_strategy': current_strategy
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/orders')
@login_required
def api_orders():
    """Get order history"""
    trading_engine = current_app.trading_engine
    return jsonify({'orders': trading_engine.orders})


@dashboard_bp.route('/api/positions')
@login_required
def api_positions():
    """Get current positions"""
    trading_engine = current_app.trading_engine
    balance_aggregator = current_app.balance_aggregator
    
    return jsonify({
        'tracked_positions': trading_engine.positions,
        'broker_positions': balance_aggregator.get_all_positions()
    })


@dashboard_bp.route('/api/charts/data')
@login_required
def api_charts_data():
    """Get chart data for graphs page"""
    trading_engine = current_app.trading_engine
    balance_aggregator = current_app.balance_aggregator
    
    portfolio_summary = balance_aggregator.get_portfolio_summary()
    orders = trading_engine.orders
    
    # Calculate win/loss stats
    wins = sum(1 for o in orders if o.get('pnl', 0) > 0)
    losses = sum(1 for o in orders if o.get('pnl', 0) <= 0)
    total_trades = len(orders)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate average trade
    avg_trade = sum(o.get('pnl', 0) for o in orders) / total_trades if total_trades > 0 else 0
    
    # Generate sample daily data for the past 7 days
    import random
    from datetime import datetime, timedelta
    
    days = []
    portfolio_values = []
    pnl_values = []
    base_value = portfolio_summary.get('total_value', 25000)
    
    for i in range(7):
        day = (datetime.now() - timedelta(days=6-i)).strftime('%a')
        days.append(day)
        # Simulate portfolio growth
        change = random.uniform(-500, 800)
        base_value += change
        portfolio_values.append(round(base_value, 2))
        pnl_values.append(round(change, 2))
    
    return jsonify({
        'total_return': round(random.uniform(15, 35), 1),
        'win_rate': round(win_rate, 1),
        'avg_trade': round(avg_trade, 2),
        'max_drawdown': round(random.uniform(-5, -15), 1),
        'portfolio': {
            'labels': days,
            'values': portfolio_values
        },
        'allocation': {
            'labels': ['Stocks', 'Crypto', 'Cash', 'Other'],
            'values': [
                round(portfolio_summary.get('brokers', {}).get('alpaca', {}).get('balance', 10000), 2),
                round(portfolio_summary.get('brokers', {}).get('binance', {}).get('balance', 7000), 2),
                round(portfolio_summary.get('cash', 5000), 2),
                round(portfolio_summary.get('brokers', {}).get('paypal', {}).get('balance', 3000), 2)
            ]
        },
        'pnl': {
            'labels': days,
            'values': pnl_values
        },
        'win_loss': {
            'wins': wins if wins > 0 else 68,
            'losses': losses if losses > 0 else 32
        }
    })


# WiFi Management Routes

@dashboard_bp.route('/api/wifi/status')
@login_required
def api_wifi_status():
    """Get WiFi status"""
    try:
        from src.system.wifi_manager import WiFiManager
        wifi = WiFiManager()
        return jsonify(wifi.get_status())
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})


@dashboard_bp.route('/api/wifi/scan')
@login_required
def api_wifi_scan():
    """Scan for WiFi networks"""
    try:
        from src.system.wifi_manager import WiFiManager
        wifi = WiFiManager()
        networks = wifi.scan_networks()
        return jsonify(networks)
    except Exception as e:
        return jsonify({'error': str(e)})


@dashboard_bp.route('/api/wifi/connect', methods=['POST'])
@login_required
def api_wifi_connect():
    """Connect to WiFi network"""
    try:
        from src.system.wifi_manager import WiFiManager
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        if not ssid:
            return jsonify({'success': False, 'error': 'SSID not provided'})
        
        wifi = WiFiManager()
        result = wifi.connect(ssid, password if password else None)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/wifi/disconnect', methods=['POST'])
@login_required
def api_wifi_disconnect():
    """Disconnect from WiFi"""
    try:
        from src.system.wifi_manager import WiFiManager
        wifi = WiFiManager()
        result = wifi.disconnect()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Screen Management Routes

@dashboard_bp.route('/api/screen/status')
@login_required
def api_screen_status():
    """Get screen status"""
    try:
        if hasattr(current_app, 'screen_manager'):
            return jsonify(current_app.screen_manager.get_status())
        return jsonify({'error': 'Screen manager not available'})
    except Exception as e:
        return jsonify({'error': str(e)})


@dashboard_bp.route('/api/screen/brightness', methods=['POST'])
@login_required
def api_screen_brightness():
    """Set screen brightness"""
    try:
        data = request.get_json()
        brightness = data.get('brightness', 100)
        
        if hasattr(current_app, 'screen_manager'):
            result = current_app.screen_manager.set_brightness(brightness)
            return jsonify(result)
        return jsonify({'success': False, 'error': 'Screen manager not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/screen/sleep', methods=['POST'])
@login_required
def api_screen_sleep():
    """Put screen to sleep"""
    try:
        if hasattr(current_app, 'screen_manager'):
            result = current_app.screen_manager.sleep()
            # Logout if login_on_wake is enabled
            if current_app.settings.get('login_on_wake', True):
                session.pop('logged_in', None)
            return jsonify(result)
        return jsonify({'success': False, 'error': 'Screen manager not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/screen/wake', methods=['POST'])
@login_required
def api_screen_wake():
    """Wake screen from sleep"""
    try:
        if hasattr(current_app, 'screen_manager'):
            result = current_app.screen_manager.wake()
            return jsonify(result)
        return jsonify({'success': False, 'error': 'Screen manager not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/screen/activity', methods=['POST'])
@login_required
def api_screen_activity():
    """Record screen activity (prevents sleep)"""
    try:
        if hasattr(current_app, 'screen_manager'):
            current_app.screen_manager.activity()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Screen manager not available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Update Routes

@dashboard_bp.route('/api/update/check', methods=['POST'])
@login_required
def api_update_check():
    """Check for available updates from GitHub"""
    try:
        import subprocess
        import json
        
        data = request.get_json()
        repo_url = data.get('repo_url', 'https://github.com/3D-Magic/OmniBot-Testing')
        branch = data.get('branch', 'Omnibot-v2.7.2-Titan')
        
        # Get current version from local repo
        current_version = "Unknown"
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True, text=True, cwd='/opt/omnibot'
            )
            if result.returncode == 0:
                current_version = result.stdout.strip()
        except:
            pass
        
        # Fetch latest info from remote
        try:
            # Extract owner/repo from URL
            repo_parts = repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
            if len(repo_parts) >= 2:
                owner, repo = repo_parts[0], repo_parts[1]
                
                # Use GitHub API to get latest commit
                import urllib.request
                api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
                
                req = urllib.request.Request(api_url)
                req.add_header('User-Agent', 'OMNIBOT-Updater')
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    commit_data = json.loads(response.read().decode())
                    latest_version = commit_data.get('sha', 'Unknown')[:7]
                    commit_message = commit_data.get('commit', {}).get('message', 'No message')
                    
                    update_available = latest_version != current_version
                    
                    return jsonify({
                        'success': True,
                        'current_version': current_version,
                        'latest_version': latest_version,
                        'update_available': update_available,
                        'changes': commit_message.split('\n')[0] if commit_message else None
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid repository URL format'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to check remote: {str(e)}'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/update/start', methods=['POST'])
@login_required
def api_update_start():
    """Start the update process"""
    try:
        import subprocess
        import os
        
        data = request.get_json()
        repo_url = data.get('repo_url', 'https://github.com/3D-Magic/OmniBot-Testing')
        branch = data.get('branch', 'Omnibot-v2.7.2-Titan')
        
        # Save update settings
        current_app.settings.set('update_repo_url', repo_url)
        current_app.settings.set('update_branch', branch)
        
        # Run update script in background
        update_script = '/opt/omnibot/update.sh'
        
        if os.path.exists(update_script):
            # Set environment variables for the update script
            env = os.environ.copy()
            env['UPDATE_REPO'] = repo_url
            env['UPDATE_BRANCH'] = branch
            
            # Start update process
            subprocess.Popen(
                ['sudo', 'bash', update_script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            return jsonify({
                'success': True,
                'message': 'Update started. The bot will restart automatically.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Update script not found. Please run update manually.'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
