# OMNIBOT v2.7 Titan - Modular Edition

A fully modular cryptocurrency and stock trading bot for Raspberry Pi.

## Features

- **Modular Architecture**: Each component is independent and testable
- **Multiple Brokers**: Alpaca (Stocks), Binance (Crypto), Interactive Brokers (Forex)
- **Web Dashboard**: Real-time portfolio tracking
- **WiFi Management**: Built-in network scanning and connection
- **Session Persistence**: Reliable login with 24-hour sessions

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/omnibot.git
cd omnibot/omnibot_modular
chmod +x install.sh
sudo ./install.sh
```

### 2. Access Dashboard

Open your browser to:
```
http://<raspberry-pi-ip>:8081
```

Default login: `admin` / `admin`

### 3. Configure Brokers

Go to Settings and enter your API keys:
- **Alpaca**: Get keys from [alpaca.markets](https://alpaca.markets)
- **Binance**: Get keys from [Binance Testnet](https://testnet.binance.vision)
- **IB Gateway**: Enter your IB account credentials

## Manual Installation

If the install script doesn't work:

```bash
# Create directories
sudo mkdir -p /opt/omnibot /etc/omnibot

# Copy files
sudo cp -r * /opt/omnibot/

# Create virtual environment
sudo python3 -m venv /opt/omnibot/venv
sudo /opt/omnibot/venv/bin/pip install -r requirements.txt

# Create settings file
sudo tee /etc/omnibot/settings.json > /dev/null << 'EOF'
{
  "version": "v2.7.2-titan",
  "password": "admin",
  "trading_mode": "demo",
  "strategy": "moderate"
}
EOF

# Run
sudo /opt/omnibot/venv/bin/python /opt/omnibot/app.py
```

## Module Structure

```
omnibot_modular/
├── app.py                 # Main entry point
├── config/               # Settings management
├── brokers/              # Broker API wrappers
│   ├── alpaca_config.py
│   ├── binance_config.py
│   ├── ib_gateway_config.py
│   └── balance_aggregator.py
├── engine/               # Trading logic
├── visualization/        # Dashboard routes
├── wifi/                 # WiFi management
└── templates/            # HTML templates
```

## Testing Individual Modules

### Test Alpaca
```python
from brokers import AlpacaConfig

alpaca = AlpacaConfig(api_key='PK...', secret_key='...', paper=True)
if alpaca.connect():
    print(f"Balance: ${alpaca.get_balance()}")
```

### Test Binance
```python
from brokers import BinanceConfig

binance = BinanceConfig(api_key='...', secret_key='...', testnet=True)
if binance.connect():
    print(f"Balance: ${binance.get_balance()}")
```

### Test WiFi
```python
from wifi import WiFiManager

wifi = WiFiManager()
networks = wifi.scan_networks()
print(f"Found {len(networks)} networks")
```

## Troubleshooting

### Login Issues
- Sessions are stored in `/tmp/flask_session/`
- Clear this directory if you get stuck: `sudo rm -rf /tmp/flask_session/*`

### Service Won't Start
```bash
# Check status
sudo systemctl status omnibot-dashboard

# View logs
sudo journalctl -u omnibot-dashboard -f

# Restart
sudo systemctl restart omnibot-dashboard
```

### Broker Connection Fails
- Verify API keys in Settings
- Check broker status in Dashboard
- Test individual brokers using Python (see Testing section)

## Security Notes

- Change default password after first login
- API keys are stored in `/etc/omnibot/settings.json` (restricted permissions)
- Use environment variable `SECRET_KEY` for production
- Run in `demo` mode until you're confident with live trading

## License

MIT License - See LICENSE file
