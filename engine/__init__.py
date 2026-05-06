"""
Engine Module
AI-Powered trading logic and execution
"""
from .ai_trading_engine import AITradingEngine, OrderSide, OrderType

# Alias for backward compatibility
TradingEngine = AITradingEngine

__all__ = ['AITradingEngine', 'TradingEngine', 'OrderSide', 'OrderType']
