# OMNIBOT v2.7.2 Titan

A fully functional, multi-broker trading bot for Raspberry Pi 5 with a modern web dashboard, real-time trading capabilities, and comprehensive system management.

## Features

<img width="1607" height="753" alt="image" src="https://github.com/user-attachments/assets/86cb5841-34e9-40fd-afa2-72f9547a0f82" />

### Trading Features
- **7 Selectable Trading Strategies**:
  - Scalping (1-5 min, high frequency)
  - Day Trading (5-15 min, intraday)
  - Swing Trading (daily, multi-day holds) - Default
  - Momentum (trend following with volume)
  - Mean Reversion (Bollinger Bands based)
  - Breakout (support/resistance levels)
  - Trend Following (SMA crossovers)

- **Multi-Broker Support**:
  - Alpaca (Stocks & ETFs)
  - Binance (Cryptocurrency)
  - PayPal (Central wallet tracking)
  - Interactive Brokers (via TWS/Gateway)

- **Risk Management**:
  - Configurable stop loss (default 5%)
  - Configurable take profit (default 10%)
  - Trailing stops
  - Position size limits
  - Daily loss limits
  - Sell-all-profitable feature

### Dashboard Features
- Modern, responsive web interface
- Real-time portfolio tracking
- Live position monitoring
- Order history with filtering
- Interactive charts (6 chart types)
- Dark theme optimized for trading

### System Features (Raspberry Pi)
- **WiFi Management**: Scan, connect, disconnect from dashboard
- **Screen Control**: Brightness adjustment, sleep timer
- **Kiosk Mode**: Fullscreen dashboard on boot
- **VNC Access**: Remote desktop access
- **Auto-login Security**: Login required on screen wake

## Installation

### Raspberry Pi 5 (Debian Trixie)

```bash
# Download the install script
curl -fsSL https://raw.githubusercontent.com/3D-Magic/OmniBot-Testing/Omnibot-v2.7.2-Titan/install_pi.sh -o install_pi.sh

# Run the installer
sudo bash install_pi.sh
```

### Manual Installation

```bash
# Clone the repository
git clone -b Omnibot-v2.7.2-Titan https://github.com/3D-Magic/OmniBot-Testing.git
cd OmniBot-Testing

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python app.py
```

## Configuration

### 1. API Keys (Required)

Navigate to Settings → API Keys in the dashboard and configure:

#### Alpaca (Stocks)
- Get API keys from [Alpaca Markets](https://alpaca.markets/)
- Enable paper trading for testing
- Recommended: Start with paper trading

#### Binance (Crypto)
- Get API keys from [Binance](https://www.binance.com/)
- Enable testnet for testing
- Required permissions: Spot trading

#### PayPal (Optional Wallet)
- Get credentials from [PayPal Developer](https://developer.paypal.com/)
- Use sandbox for testing
- Enables central wallet tracking

#### Interactive Brokers (Optional)
- Requires TWS or IB Gateway running
- Default port: 7497 (TWS) or 7496 (Gateway)

### 2. Trading Strategy

Navigate to Settings → Strategies and select:

| Strategy | Risk | Timeframe | Target |
|----------|------|-----------|--------|
| Scalping | High | 1-5 min | 0.5-1% |
| Day Trading | Medium | 5-15 min | 1-3% |
| Swing Trading | Medium | Daily | 5-10% |
| Momentum | High | Daily | 8-15% |
| Mean Reversion | Medium | Daily | 3-6% |
| Breakout | High | Daily | 10-20% |
| Trend Following | Medium | Daily | 10-20% |

### 3. Risk Management

Configure in Settings → Risk Management:
- Stop Loss: Default 5%
- Take Profit: Default 10%
- Max Position Size: Default 10%
- Max Daily Loss: Default 5%

### 4. Screen Settings (Pi)

Navigate to Settings → Display & Screen:
- Brightness: 10-100%
- Sleep Timer: 1, 5, 10, or 30 minutes
- Login on Wake: Enabled by default

### 5. WiFi Management

Navigate to Settings → WiFi Network:
- Click "Scan" to find networks
- Click "Connect" and enter password
- View connection status and signal strength

## Usage

### Starting the Bot

```bash
# Start the service
sudo systemctl start omnibot

# View status
sudo systemctl status omnibot

# View logs
sudo journalctl -u omnibot -f
```

### Accessing the Dashboard

- **Local**: http://localhost:8081
- **Network**: http://[pi-ip-address]:8081
- **Default Login**: admin / admin

### VNC Access

- **Address**: [pi-ip-address]:5900
- Use RealVNC Viewer or any VNC client

### Kiosk Mode

The dashboard automatically starts in fullscreen on boot. To disable:

```bash
sudo systemctl disable omnibot-kiosk
```

## Trading Controls

### Dashboard Buttons
- **Start Trading**: Begin automated trading
- **Stop Trading**: Halt all trading activity
- **Sell All**: Sell all positions immediately
- **Sell Profitable**: Sell only profitable positions, disable buying

### Re-enabling Buying

After "Sell Profitable", buying is disabled. To re-enable:

```bash
# Via API
curl -X POST http://localhost:8081/api/trading/enable_buying \
  -H "Content-Type: application/json"
```

Or use the dashboard button (if implemented).

## File Structure

```
/opt/omnibot/
├── app.py                    # Main application
├── config/
│   ├── constants.py          # Default settings
│   ├── settings.py           # Settings manager
│   └── settings.json         # User settings (created on first run)
├── brokers/
│   ├── alpaca_config.py      # Alpaca integration
│   ├── binance_config.py     # Binance integration
│   ├── paypal_wallet.py      # PayPal wallet
│   ├── ib_gateway_config.py  # Interactive Brokers
│   └── balance_aggregator.py # Portfolio aggregation
├── engine/
│   ├── trading_engine.py     # Core trading logic
│   └── strategies.py         # Trading strategies
├── src/
│   ├── dashboard/
│   │   ├── routes.py         # Web routes
│   │   └── __init__.py
│   └── system/
│       ├── wifi_manager.py   # WiFi management
│       └── screen_manager.py # Screen control
├── templates/                # HTML templates
├── static/                   # CSS, JS, images
├── logs/                     # Log files
├── data/                     # Data storage
└── venv/                     # Python virtual environment
```

## API Endpoints

### Trading
- `POST /api/trading/start` - Start trading
- `POST /api/trading/stop` - Stop trading
- `POST /api/trading/sell_all` - Sell all positions
- `POST /api/trading/sell_all_profitable` - Sell profitable only
- `POST /api/trading/enable_buying` - Re-enable buying
- `POST /api/trading/strategy` - Change strategy

### Data
- `GET /api/status` - System status
- `GET /api/portfolio` - Portfolio summary
- `GET /api/positions` - Current positions
- `GET /api/orders` - Order history
- `GET /api/charts/data` - Chart data

### Settings
- `GET /api/settings` - Get all settings
- `POST /api/settings` - Update settings
- `POST /api/settings/reset` - Reset to defaults
- `POST /api/broker/config` - Update broker config
- `POST /api/broker/test` - Test broker connection

### WiFi (Pi)
- `GET /api/wifi/status` - WiFi status
- `GET /api/wifi/scan` - Scan networks
- `POST /api/wifi/connect` - Connect to network
- `POST /api/wifi/disconnect` - Disconnect

### Screen (Pi)
- `GET /api/screen/status` - Screen status
- `POST /api/screen/brightness` - Set brightness
- `POST /api/screen/sleep` - Put screen to sleep
- `POST /api/screen/wake` - Wake screen
- `POST /api/screen/activity` - Record activity

## Safety Features

1. **Paper Trading Default**: All brokers start in paper/test mode
2. **Buying Disable**: After sell-all, buying is disabled until manually re-enabled
3. **Position Limits**: Maximum position size prevents over-concentration
4. **Stop Losses**: Automatic loss protection
5. **Login on Wake**: Security when screen wakes from sleep

## Troubleshooting

### Bot won't start
```bash
# Check logs
sudo journalctl -u omnibot -f

# Check Python dependencies
cd /opt/omnibot
source venv/bin/activate
pip list | grep -E "flask|alpaca|binance"
```

### Dashboard not accessible
```bash
# Check if service is running
sudo systemctl status omnibot

# Check port
sudo netstat -tlnp | grep 8081
```

### WiFi not connecting
```bash
# Check WiFi status
nmcli device status

# Scan networks
nmcli dev wifi list
```

### Screen brightness not working
```bash
# Check backlight path
ls /sys/class/backlight/

# Test manual control
echo 100 | sudo tee /sys/class/backlight/*/brightness
```

## Updating

```bash
sudo /opt/omnibot/update.sh
```

## Uninstalling

```bash
sudo /opt/omnibot/uninstall.sh
```

## Security Notes

1. **Change default password**: Update in Settings → Security
2. **Use paper trading**: Test thoroughly before live trading
3. **Enable login on wake**: Prevents unauthorized access
4. **Secure API keys**: Never commit keys to version control
5. **Use HTTPS**: For production, configure SSL/TLS

## Disclaimer

**Trading involves significant risk of loss. This software is provided as-is without warranties. Always:**
- Test thoroughly in paper trading mode first
- Never trade with money you cannot afford to lose
- Understand the strategy before using it
- Monitor the bot regularly
- Keep software updated

## License

Personal Use License - See LICENSE file for details

## Support

- GitHub Issues: https://github.com/3D-Magic/OmniBot-Testing/issues
- Documentation: See docs/ folder

---

**OMNIBOT v2.7.2 Titan** - Trade smarter, not harder.
