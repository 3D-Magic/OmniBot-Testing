"""
Graph Plotter
Generates charts and visualizations for the dashboard
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)


class GraphPlotter:
    """Generates chart data for dashboard visualization"""
    
    def __init__(self):
        self._history = []  # Store historical data points
        self._max_history = 100  # Keep last 100 data points
    
    def add_data_point(self, total_capital: float):
        """Add a new data point to history"""
        self._history.append({
            'timestamp': datetime.now().isoformat(),
            'value': total_capital
        })
        
        # Trim history if too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_portfolio_chart_data(self, timeframe='1D') -> Dict:
        """Generate portfolio value chart data"""
        # Filter data based on timeframe
        now = datetime.now()
        
        if timeframe == '1H':
            cutoff = now - timedelta(hours=1)
        elif timeframe == '1D':
            cutoff = now - timedelta(days=1)
        elif timeframe == '1W':
            cutoff = now - timedelta(weeks=1)
        elif timeframe == '1M':
            cutoff = now - timedelta(days=30)
        else:
            cutoff = now - timedelta(days=1)
        
        # Filter and format data
        filtered = [
            point for point in self._history
            if datetime.fromisoformat(point['timestamp']) >= cutoff
        ]
        
        if not filtered:
            # Generate demo data if no history
            filtered = self._generate_demo_data()
        
        labels = []
        values = []
        
        for point in filtered:
            dt = datetime.fromisoformat(point['timestamp'])
            labels.append(dt.strftime('%H:%M'))
            values.append(point['value'])
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Total Capital',
                'data': values,
                'borderColor': '#00d4ff',
                'backgroundColor': 'rgba(0, 212, 255, 0.1)',
                'fill': True,
                'tension': 0.4
            }]
        }
    
    def get_allocation_chart_data(self, balances: Dict) -> Dict:
        """Generate asset allocation pie chart data"""
        data = {
            'labels': ['Stocks', 'Crypto', 'Forex', 'Cash'],
            'datasets': [{
                'data': [
                    balances.get('stocks', 0),
                    balances.get('crypto', 0),
                    balances.get('forex', 0),
                    balances.get('cash', 0)
                ],
                'backgroundColor': [
                    '#00d4ff',  # Stocks - cyan
                    '#00ff88',  # Crypto - green
                    '#ff6b6b',  # Forex - red
                    '#ffd93d'   # Cash - yellow
                ]
            }]
        }
        return data
    
    def get_broker_comparison_data(self, broker_data: Dict) -> Dict:
        """Generate broker balance comparison chart"""
        labels = []
        values = []
        colors = []
        
        color_map = {
            'alpaca': '#00d4ff',
            'binance': '#00ff88',
            'ibkr': '#ff6b6b',
            'ig': '#9b59b6'
        }
        
        for name, data in broker_data.items():
            if data.get('configured') and data.get('balance', 0) > 0:
                labels.append(name.title())
                values.append(data['balance'])
                colors.append(color_map.get(name, '#cccccc'))
        
        return {
            'labels': labels,
            'datasets': [{
                'data': values,
                'backgroundColor': colors
            }]
        }
    
    def _generate_demo_data(self) -> List[Dict]:
        """Generate demo chart data"""
        data = []
        now = datetime.now()
        base_value = 100000
        
        for i in range(24):
            time = now - timedelta(hours=23-i)
            # Create some variation
            import math
            variation = math.sin(i * 0.5) * 5000 + (i * 100)
            data.append({
                'timestamp': time.isoformat(),
                'value': base_value + variation
            })
        
        return data
    
    def clear_history(self):
        """Clear chart history"""
        self._history = []
