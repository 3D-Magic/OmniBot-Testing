"""
OMNIBOT v2.7 Titan - Flask Dashboard Application
Multi-market support with profit tracking
"""

import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from functools import wraps

logger = logging.getLogger(__name__)


def create_app(engine=None):
    """Create Flask application factory"""
    
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'omnibot-secret-key')
    app.config['DEBUG'] = False
    
    # Store engine reference
    app.engine = engine
    
    # Auth decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            password = request.form.get('password', '')
            # Simple password check
            from config.settings import DASHBOARD
            if password == DASHBOARD.get('password', 'admin'):
                session['logged_in'] = True
                return redirect(url_for('index'))
            return render_template('login.html', error='Invalid password')
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        session.pop('logged_in', None)
        return redirect(url_for('login'))
    
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')
    
    @app.route('/api/status')
    @login_required
    def api_status():
        if app.engine:
            return jsonify({
                'status': 'running',
                'markets': app.engine.get_market_status(),
                'portfolio': app.engine.get_portfolio_summary()
            })
        return jsonify({'status': 'stopped'})
    
    @app.route('/api/portfolio')
    @login_required
    def api_portfolio():
        if app.engine:
            return jsonify(app.engine.get_portfolio_summary())
        return jsonify({})
    
    @app.route('/api/strategy', methods=['POST'])
    @login_required
    def set_strategy():
        data = request.get_json()
        strategy = data.get('strategy', 'moderate')
        
        # Update trading mode
        from config.settings import TradingMode
        mode_map = {
            'conservative': TradingMode.CONSERVATIVE,
            'moderate': TradingMode.MODERATE,
            'aggressive': TradingMode.AGGRESSIVE,
            'hft': TradingMode.HFT,
            'sentinel': TradingMode.SENTINEL
        }
        
        if app.engine and app.engine.stock_engine:
            app.engine.stock_engine.set_mode(mode_map.get(strategy, TradingMode.MODERATE))
        
        return jsonify({'success': True, 'strategy': strategy})
    
    return app


# Legacy compatibility
try:
    from src.core.multi_market_engine import get_multi_market_engine
    engine = get_multi_market_engine()
    app = create_app(engine)
except Exception as e:
    logger.warning(f"Could not initialize engine: {e}")
    app = create_app()