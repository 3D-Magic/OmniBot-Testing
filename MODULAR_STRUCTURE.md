# OMNIBOT v2.7 Titan - Modular Architecture

## Overview
The bot has been restructured into independent modules. Each module has a single responsibility and can be tested/worked on independently.

## Directory Structure

```
omnibot_modular/
├── app.py                      # Main entry point (200 lines)
├── config/                     # Configuration layer
│   ├── __init__.py
│   ├── constants.py            # App constants, defaults
│   └── settings.py             # Settings persistence (80 lines)
├── brokers/                    # Broker API layer
│   ├── __init__.py
│   ├── base_broker.py          # Abstract base class
│   ├── alpaca_config.py        # Alpaca wrapper (100 lines)
│   ├── binance_config.py       # Binance wrapper (100 lines)
│   ├── ib_gateway_config.py    # IB Gateway wrapper (120 lines)
│   └── balance_aggregator.py   # Combines all brokers (130 lines)
├── engine/                     # Trading logic layer
│   ├── __init__.py
│   └── trading_engine.py       # Core trading engine (200 lines)
├── visualization/              # Presentation layer
│   ├── __init__.py
│   ├── dashboard_routes.py     # Flask routes (200 lines)
│   └── graph_plotter.py        # Chart generation (120 lines)
├── wifi/                       # Network layer
│   ├── __init__.py
│   └── wifi_manager.py         # WiFi operations (140 lines)
├── templates/                  # HTML templates (visual only)
│   ├── index.html
│   ├── settings.html
│   └── login.html
├── static/                     # CSS/JS assets
│   ├── css/
│   └── js/
└── requirements.txt
```

## Module Dependencies

```
app.py (top level)
    ├─ config (no dependencies)
    ├─ brokers (uses config)
    │   └─ balance_aggregator (uses all brokers)
    ├─ wifi (no dependencies)
    ├─ engine (uses brokers, config)
    └─ visualization (uses config, brokers, wifi, engine)
```

## Key Features

### 1. Independent Broker Modules
Each broker can be tested independently:

```python
from brokers import AlpacaConfig

alpaca = AlpacaConfig(api_key='...', secret_key='...')
if alpaca.connect():
    balance = alpaca.get_balance()
    print(f"Alpaca balance: ${balance}")
```

### 2. Balance Aggregator
Combines all brokers transparently:

```python
from brokers import BalanceAggregator

aggregator = BalanceAggregator()
aggregator.add_broker('alpaca', alpaca)
aggregator.add_broker('binance', binance)

# Get all balances in one call
data = aggregator.get_all_balances()
print(f"Total: ${data['total_capital']}")
print(f"Stocks: ${data['stocks']}")
print(f"Crypto: ${data['crypto']}")
```

### 3. Clean Separation
- **Dashboard** = Visual only (HTML/CSS/JS)
- **Backend** = All data processing
- **Settings** = Just stores/retrieves data
- **Brokers** = Just API wrappers

### 4. Easy Testing
Each module can be tested independently:

```bash
# Test Alpaca module
python -c "from brokers.alpaca_config import AlpacaConfig; ..."

# Test WiFi module
python -c "from wifi.wifi_manager import WiFiManager; ..."

# Test Settings
python -c "from config.settings import Settings; s = Settings(); print(s.all())"
```

## Migration from Old Code

The old `dashboard.py` (584 lines) has been split into:
- `app.py` (entry point)
- `brokers/*` (broker APIs)
- `visualization/dashboard_routes.py` (routes)
- `config/settings.py` (persistence)
- `wifi/wifi_manager.py` (WiFi)

## Benefits

1. **Maintainability**: Each file < 200 lines
2. **Testability**: Test each broker independently
3. **Extensibility**: Add new brokers without touching existing code
4. **Collaboration**: Multiple developers can work on different modules
5. **Debugging**: Isolate issues to specific modules

## Adding a New Broker (Example: Kraken)

1. Create `brokers/kraken_config.py`:
```python
from .base_broker import BaseBroker

class KrakenConfig(BaseBroker):
    def __init__(self, api_key, secret_key):
        super().__init__('kraken')
        self.api_key = api_key
        self.secret_key = secret_key
    
    def connect(self) -> bool:
        # Implementation
        pass
    
    def get_balance(self) -> float:
        # Implementation
        pass
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)
```

2. Register in `app.py`:
```python
from brokers import KrakenConfig

if settings.is_configured('kraken'):
    kraken = KrakenConfig(...)
    balance_aggregator.add_broker('kraken', kraken)
```

3. Done! No other files need changes.
