"""
OMNIBOT v2.7 Titan - Utilities
"""

import logging
import os
from datetime import datetime


def setup_logging(log_dir: str = "data/logs"):
    """Setup logging configuration"""
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"omnibot_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def format_currency(value: float, currency: str = "$") -> str:
    """Format value as currency"""
    return f"{currency}{value:,.2f}"


def calculate_percentage_change(old: float, new: float) -> float:
    """Calculate percentage change"""
    if old == 0:
        return 0
    return ((new - old) / old) * 100