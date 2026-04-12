#!/usr/bin/env python3
"""
OMNIBOT Module Verification Script
Tests all modules to ensure they work correctly
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger(__name__)


def test_config():
    """Test config module"""
    logger.info("=" * 50)
    logger.info("Testing Config Module")
    logger.info("=" * 50)
    
    try:
        from config import Settings, DEFAULT_SETTINGS
        
        # Test settings creation
        settings = Settings(filepath='/tmp/test_settings.json')
        assert settings.get('version') == DEFAULT_SETTINGS['version']
        
        # Test password verification
        settings.set('password', 'test123')
        assert settings.verify_password('test123') == True
        assert settings.verify_password('wrong') == False
        
        # Test change password
        settings.change_password('newpass')
        assert settings.verify_password('newpass') == True
        
        logger.info("✓ Config module working")
        return True
    except Exception as e:
        logger.error(f"✗ Config module failed: {e}")
        return False


def test_brokers():
    """Test broker modules"""
    logger.info("=" * 50)
    logger.info("Testing Broker Modules")
    logger.info("=" * 50)
    
    try:
        from brokers import AlpacaConfig, BinanceConfig, BalanceAggregator
        
        # Test Alpaca (without real keys)
        alpaca = AlpacaConfig(api_key='', secret_key='')
        assert alpaca.is_configured() == False
        assert alpaca.is_configured() == False  # Empty keys = not configured
        
        alpaca_configured = AlpacaConfig(api_key='PK123', secret_key='secret')
        assert alpaca_configured.is_configured() == True
        
        # Test Binance
        binance = BinanceConfig(api_key='', secret_key='')
        assert binance.is_configured() == False
        
        # Test Balance Aggregator
        agg = BalanceAggregator()
        agg.add_broker('alpaca', alpaca_configured)
        
        # Test demo mode
        demo_balances = agg.get_all_balances(demo_mode=True)
        assert demo_balances['total_capital'] == 100000.0
        assert demo_balances['is_demo'] == True
        
        logger.info("✓ Broker modules working")
        return True
    except Exception as e:
        logger.error(f"✗ Broker module failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wifi():
    """Test WiFi module"""
    logger.info("=" * 50)
    logger.info("Testing WiFi Module")
    logger.info("=" * 50)
    
    try:
        from wifi import WiFiManager
        
        wifi = WiFiManager()
        
        # Test status (should work even without WiFi)
        status = wifi.get_status()
        assert 'connected' in status
        assert 'ssid' in status
        
        logger.info("✓ WiFi module working")
        return True
    except Exception as e:
        logger.error(f"✗ WiFi module failed: {e}")
        return False


def test_engine():
    """Test trading engine"""
    logger.info("=" * 50)
    logger.info("Testing Trading Engine")
    logger.info("=" * 50)
    
    try:
        from engine import TradingEngine, OrderSide, OrderType
        from config import Settings
        from brokers import BalanceAggregator
        
        settings = Settings(filepath='/tmp/test_settings.json')
        agg = BalanceAggregator()
        engine = TradingEngine(agg, settings)
        
        # Test start/stop
        assert engine.start() == True
        assert engine.is_running == True
        
        engine.stop()
        assert engine.is_running == False
        
        # Test order placement (demo mode)
        settings.set('trading_mode', 'demo')
        engine.start()
        
        order = engine.place_order('AAPL', OrderSide.BUY, 10)
        assert order is not None
        assert order['status'] == 'filled'
        
        engine.stop()
        
        logger.info("✓ Trading engine working")
        return True
    except Exception as e:
        logger.error(f"✗ Trading engine failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visualization():
    """Test visualization module"""
    logger.info("=" * 50)
    logger.info("Testing Visualization Module")
    logger.info("=" * 50)
    
    try:
        from visualization import GraphPlotter
        
        plotter = GraphPlotter()
        
        # Test adding data points
        plotter.add_data_point(100000)
        plotter.add_data_point(100500)
        
        # Test chart generation
        chart_data = plotter.get_portfolio_chart_data()
        assert 'labels' in chart_data
        assert 'datasets' in chart_data
        
        # Test allocation chart
        alloc_data = plotter.get_allocation_chart_data({
            'stocks': 40000,
            'crypto': 35000,
            'forex': 25000
        })
        assert 'labels' in alloc_data
        
        logger.info("✓ Visualization module working")
        return True
    except Exception as e:
        logger.error(f"✗ Visualization module failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test full integration"""
    logger.info("=" * 50)
    logger.info("Testing Full Integration")
    logger.info("=" * 50)
    
    try:
        from app import create_app
        
        app, socketio = create_app()
        
        # Test Flask app exists
        assert app is not None
        
        # Test routes exist
        with app.test_client() as client:
            # Test login page loads
            response = client.get('/login')
            assert response.status_code == 200
            
            # Test API auth check
            response = client.get('/api/auth/check')
            assert response.status_code == 200
            data = response.get_json()
            assert 'authenticated' in data
        
        logger.info("✓ Full integration working")
        return True
    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 50)
    logger.info("OMNIBOT MODULE VERIFICATION")
    logger.info("=" * 50 + "\n")
    
    tests = [
        ("Config", test_config),
        ("Brokers", test_brokers),
        ("WiFi", test_wifi),
        ("Engine", test_engine),
        ("Visualization", test_visualization),
        ("Integration", test_integration)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"✗ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 50)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{name:20s} {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    logger.info("-" * 50)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ ALL TESTS PASSED - System ready!")
        return 0
    else:
        logger.info(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
