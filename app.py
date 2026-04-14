#!/usr/bin/env python3
"""
OMNIBOT v2.7.2 Titan - FULLY FUNCTIONAL TRADING BOT
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
from brokers import AlpacaConfig, BinanceConfig, PayPalWallet, BalanceAggregator
from engine import TradingEngine


def create_app():
    """Application factory - creates and configures the Flask app"""
    
    # Create Flask app
    app = Flask(__name__, template_folder='templates', static_folder='static')
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
        alpaca_config = settings.get_broker_config('alpaca')
        alpaca = AlpacaConfig(
            api_key=alpaca_config.get('api_key'),
            secret_key=alpaca_config.get('secret_key'),
            paper=alpaca_config.get('paper', True)
        )
        balance_aggregator.add_broker('alpaca', alpaca)
        if alpaca_config.get('enabled', False):
            alpaca.connect()
    
    if settings.is_configured('binance'):
        binance_config = settings.get_broker_config('binance')
        binance = BinanceConfig(
            api_key=binance_config.get('api_key'),
            secret_key=binance_config.get('secret_key'),
            testnet=binance_config.get('testnet', True)
        )
        balance_aggregator.add_broker('binance', binance)
        if binance_config.get('enabled', False):
            binance.connect()
    
    # Initialize PayPal wallet
    if settings.is_configured('paypal'):
        paypal_config = settings.get_broker_config('paypal')
        paypal = PayPalWallet(
            client_id=paypal_config.get('client_id'),
            client_secret=paypal_config.get('client_secret'),
            sandbox=paypal_config.get('sandbox', True)
        )
        balance_aggregator.add_broker('paypal', paypal)
        if paypal_config.get('enabled', False):
            paypal.connect()
    
    # Initialize Interactive Brokers (if configured)
    if settings.is_configured('interactive_brokers'):
        try:
            from brokers.ib_gateway_config import IBGatewayConfig
            ib_config = settings.get_broker_config('interactive_brokers')
            ib = IBGatewayConfig(
                host=ib_config.get('host', '127.0.0.1'),
                port=ib_config.get('port', 7497),
                client_id=ib_config.get('client_id', 1)
            )
            balance_aggregator.add_broker('interactive_brokers', ib)
            if ib_config.get('enabled', False):
                ib.connect()
        except Exception as e:
            logger.warning(f"[APP] Could not initialize Interactive Brokers: {e}")
    
    # Initialize screen manager (for Raspberry Pi)
    try:
        from src.system.screen_manager import ScreenManager
        screen_manager = ScreenManager(settings.get_all())
        app.screen_manager = screen_manager
        logger.info("[APP] Screen manager initialized")
    except Exception as e:
        logger.warning(f"[APP] Screen manager not available: {e}")
        app.screen_manager = None
    
    # Initialize trading engine
    trading_engine = TradingEngine(balance_aggregator, settings)
    
    # Store in app context
    app.settings = settings
    app.balance_aggregator = balance_aggregator
    app.trading_engine = trading_engine
    app.socketio = socketio
    
    # Import and register dashboard blueprint
    from src.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    # Start trading engine if enabled
    if settings.get('trading_enabled', False):
        trading_engine.start()
    
    logger.info("[APP] Application initialized successfully")
    
    return app, socketio


def main():
    """Main entry point"""
    app, socketio = create_app()
    
    # Get host and port from settings
    host = app.settings.get('dashboard_host', '0.0.0.0')
    port = app.settings.get('dashboard_port', 8081)
    
    logger.info(f"[APP] Starting OMNIBOT v2.7.2 Titan on {host}:{port}")
    logger.info(f"[APP] Dashboard: http://{host}:{port}")
    
    # Run with SocketIO
    socketio.run(app, host=host, port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
