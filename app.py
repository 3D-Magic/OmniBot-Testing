#!/usr/bin/env python3
"""
OMNIBOT v2.7 Titan - Modular Edition
Main application entry point
"""

import os
import sys
import logging
from flask import Flask, session
from flask_socketio import SocketIO
from flask_session import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import our modules
from config import Settings
from brokers import AlpacaConfig, BinanceConfig, IBGatewayConfig, IGConfig, BalanceAggregator
from wifi import WiFiManager
from engine import TradingEngine
from visualization import dashboard_bp, init_dashboard, GraphPlotter

def create_app():
    """Application factory - creates and configures the Flask app"""
    
    # Create Flask app
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'omnibot-secret-key-change-in-production')
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
    Session(app)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize settings
    settings = Settings()
    logger.info(f"[APP] Loaded settings from {settings.filepath}")
    
    # Initialize balance aggregator
    balance_aggregator = BalanceAggregator()
    
    # Initialize brokers from settings
    if settings.is_configured('alpaca'):
        alpaca = AlpacaConfig(
            api_key=settings.get('alpaca_key'),
            secret_key=settings.get('alpaca_secret'),
            paper=True
        )
        balance_aggregator.add_broker('alpaca', alpaca)
    
    if settings.is_configured('binance'):
        binance = BinanceConfig(
            api_key=settings.get('binance_key'),
            secret_key=settings.get('binance_secret'),
            testnet=True
        )
        balance_aggregator.add_broker('binance', binance)
    
    if settings.is_configured('ibkr'):
        ibkr = IBGatewayConfig(
            account_id=settings.get('ibkr_account_id'),
            username=settings.get('ibkr_username'),
            password=settings.get('ibkr_password')
        )
        balance_aggregator.add_broker('ibkr', ibkr)
    
    # Initialize IG if configured
    if settings.is_configured('ig'):
        ig = IGConfig(
            api_key=settings.get('ig_api_key'),
            username=settings.get('ig_username'),
            password=settings.get('ig_password'),
            account_id=settings.get('ig_account_id'),
            demo=settings.get('ig_demo', True)
        )
        balance_aggregator.add_broker('ig', ig)
    
    # Initialize WiFi manager
    wifi_manager = WiFiManager()
    
    # Initialize graph plotter
    graph_plotter = GraphPlotter()
    
    # Initialize trading engine
    trading_engine = TradingEngine(balance_aggregator, settings)
    
    # Start trading engine if trading is enabled
    if settings.get('trading_enabled', False):
        trading_engine.start()
        logger.info("[APP] Trading engine started (enabled in settings)")
    else:
        logger.info("[APP] Trading engine ready but not started (trading_enabled=false)")
    
    # Initialize dashboard blueprint with dependencies
    init_dashboard(settings, balance_aggregator, wifi_manager)
    app.register_blueprint(dashboard_bp)
    
    # Store references on app for access from routes
    app.settings = settings
    app.balance_aggregator = balance_aggregator
    app.wifi_manager = wifi_manager
    app.graph_plotter = graph_plotter
    app.trading_engine = trading_engine
    
    # Background thread for portfolio updates
    import threading
    import time
    
    def portfolio_updater():
        """Background thread to periodically update portfolio data"""
        while True:
            try:
                # Get fresh balances
                balances = balance_aggregator.get_all_balances()
                
                # Add to graph history
                graph_plotter.add_data_point(balances.get('total_capital', 0))
                
                # Emit via SocketIO
                socketio.emit('portfolio_update', balances)
                
                logger.debug(f"[UPDATER] Portfolio updated: ${balances.get('total_capital', 0):.2f}")
                
            except Exception as e:
                logger.error(f"[UPDATER ERROR] {e}")
            
            time.sleep(10)  # Update every 10 seconds
    
    # Start background updater
    updater_thread = threading.Thread(target=portfolio_updater, daemon=True)
    updater_thread.start()
    logger.info("[APP] Started portfolio updater thread")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def server_error(e):
        return {'error': 'Internal server error'}, 500
    
    # Make session permanent on each request
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    logger.info("[APP] Flask application initialized successfully")
    
    return app, socketio


def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("OMNIBOT v2.7 Titan - Modular Edition")
    logger.info("=" * 50)
    
    app, socketio = create_app()
    
    # Run the app
    # Run the app
    # Use allow_unsafe_werkzeug=True for production with systemd
    socketio.run(
        app,
        host='0.0.0.0',
        port=8081,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )


if __name__ == '__main__':
    main()
