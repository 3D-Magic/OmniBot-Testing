# 🤖 OMNIBOT TITAN v2.7.2

[![Version](https://img.shields.io/badge/version-2.7.2-blue.svg)](https://github.com/omnibot/omnibot-titan)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Personal%20Use-red.svg)](LICENSE)

**Professional Algorithmic Trading Bot with Real Order Execution**

OMNIBOT TITAN is a complete trading system that supports multiple brokers (Alpaca, Binance, PayPal) with real order execution, a beautiful web dashboard, and touch keyboard support for Raspberry Pi displays.

![Dashboard Preview](docs/images/dashboard-preview.png)

<img width="1263" height="659" alt="image" src="https://github.com/user-attachments/assets/1e8a870d-e872-49da-9162-0eedfaedcab7" />

## ✨ Features

### Trading
- ✅ **Alpaca** - Paper & Live trading (Stocks/ETFs)
- ✅ **Binance** - Testnet & Live trading (Crypto)
- ✅ **PayPal** - Balance tracking
- ✅ **Real order execution** - Not a simulator
- ✅ **Manual trading** - Place orders via web interface
- ✅ **6 automated strategies** - Scalping, Day Trading, Swing, Momentum, Mean Reversion, Breakout

### Display
- ✅ **Touch keyboard** - JavaScript keyboard for all input fields
- ✅ **Kiosk mode** - PyQt5 browser (no Chromium crashes on Pi)
- ✅ **Auto-login** - Boots straight to dashboard
- ✅ **Pi optimized** - Works on all Raspberry Pi models

### System
- ✅ **Auto-start** - Starts on boot
- ✅ **Web dashboard** - Access from any device
- ✅ **Real-time updates** - Live portfolio data
- ✅ **Position tracking** - Monitor all positions
- ✅ **Order history** - View all executed orders

## 🚀 Quick Start

### Requirements
- Raspberry Pi (3, 4, 5, or Zero 2 W) OR any Linux/macOS/Windows machine
- Python 3.8+
- Internet connection

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/omnibot-titan.git
cd omnibot-titan

# Install Python dependencies
pip install -r requirements.txt

# On Raspberry Pi, also install display packages
sudo apt-get install python3-pyqt5 python3-pyqt5.qtwebengine

# Run the bot
python src/app.py
```

### Access Dashboard

Open your browser and go to: `http://localhost:8081`

**Default Login:**
- Username: `admin`
- Password: `admin`

## ⚙️ Configuration

### Add API Keys

1. Login to the dashboard
2. Go to **Settings** page
3. Enter your API keys:

**Alpaca:**
- Get keys at https://app.alpaca.markets/
- Paper trading: Use paper keys for testing
- Live trading: Use live keys (be careful!)

**Binance:**
- Get keys at https://www.binance.com/en/my/settings/api-management
- Testnet: Use testnet keys for testing
- Live trading: Use real keys (be careful!)

**PayPal:**
- Get keys at https://developer.paypal.com/
- Sandbox: Use sandbox for testing
- Live: Use live keys for real transactions

4. Click **Save Settings**
5. Click **Test Connections** to verify

## 📊 Dashboard Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Portfolio overview, trading status |
| **Positions** | View all open positions |
| **Orders** | Order history and status |
| **Trade** | Manual order placement |
| **Graphs** | Charts and analytics |
| **Strategy** | Select and configure strategies |
| **Settings** | Configure API keys and risk |
| **Logs** | System logs |

## 🛠️ Raspberry Pi Installation

For a complete Pi setup with auto-start and kiosk mode:

```bash
# Run the install script
sudo ./scripts/install.sh

# Reboot
sudo reboot
```

After reboot, the Pi will:
1. Auto-login as `omnibot` user
2. Start the OMNIBOT backend
3. Launch the kiosk display

## 🔧 Commands

```bash
# Start the bot
python src/app.py

# Start kiosk display (on Pi)
python src/kiosk.py

# View logs
sudo journalctl -u omnibot -f
```

## 📁 Project Structure

```
omnibot-titan/
├── src/
│   ├── app.py           # Main trading bot
│   └── kiosk.py         # PyQt5 kiosk browser
├── templates/           # HTML templates
├── static/
│   ├── css/            # Stylesheets
│   └── js/             # JavaScript
├── config/
│   └── settings.json   # Configuration
├── scripts/
│   └── install.sh      # Installation script
├── docs/               # Documentation
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## ⚠️ Risk Warning

**Trading involves risk of loss. Only trade with money you can afford to lose.**

- Start with **paper trading** to test strategies
- Use **stop losses** to limit downside
- Monitor positions regularly
- Never risk more than you can afford to lose

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 License

This project is licensed under the Personal Use License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [Alpaca](https://alpaca.markets/) for their trading API
- [Binance](https://www.binance.com/) for their crypto API
- [Flask](https://flask.palletsprojects.com/) for the web framework

---

**Version:** 2.7.2  
**Last Updated:** 18/04/2026
