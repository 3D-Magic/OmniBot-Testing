# 🤖 OMNIBOT TITAN v2.7.2

[![Version](https://img.shields.io/badge/version-2.7.2-blue.svg)](https://github.com/omnibot/omnibot-titan)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Personal%20Use-red.svg)](LICENSE)

**Professional Algorithmic Trading Bot with Real Order Execution**

OMNIBOT TITAN is a complete trading system that supports multiple brokers (Alpaca, Binance, PayPal) with real order execution, a beautiful web dashboard, and touch keyboard support for Raspberry Pi displays.

<img width="1262" height="650" alt="image" src="https://github.com/user-attachments/assets/92c487c2-b711-49eb-872b-978758538dc6" />

## ✨ Features

### Trading
- ✅ **Alpaca** - Paper & Live trading (Stocks/ETFs)
- ✅ **Binance** - Testnet & Live trading (Crypto)
- ✅ **PayPal** - Balance tracking
- ✅ **Real order execution** - Not a simulator
- ✅ **Manual trading** - Place orders via web interface
- ✅ **6 automated strategies** - Scalping, Day Trading, Swing, Momentum, Mean Reversion, Breakout

### Display
- ✅ **Touch keyboard** - Server-side injected keyboard for touchscreen input
- ✅ **Kiosk mode** - Chromium browser in fullscreen kiosk mode
- ✅ **Auto-login** - Boots straight to dashboard via LightDM
- ✅ **Pi optimized** - Tested on Raspberry Pi 5 with official touchscreen

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
git clone https://github.com/3D-Magic/OmniBot-Testing.git
cd OmniBot-Testing

# Install Python dependencies
pip3 install -r requirements.txt

# On Raspberry Pi, also install system packages
sudo apt-get install -y chromium-browser unclutter network-manager

# Run the bot
python3 src/app.py
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

OMNIBOT TITAN is designed to run headless on a Raspberry Pi with a touchscreen display. Follow this guide for a production-ready setup.

### Recommended OS

**Raspberry Pi OS (Legacy 64-bit)** with desktop environment

- Use the official Raspberry Pi Imager
- Select **Raspberry Pi OS (Legacy, 64-bit)** — this provides the best compatibility with LXDE + LightDM
- Enable SSH and configure WiFi in the imager advanced options

> ⚠️ **Do not use the "Lite" version** — the bot requires a desktop environment for kiosk mode.

### Pi Setup Steps

```bash
# 1. Update the system
sudo apt update && sudo apt full-upgrade -y

# 2. Install required system packages
sudo apt install -y \
    chromium-browser \
    unclutter \
    xdotool \
    git \
    python3-pip \
    python3-venv \
    network-manager

# 3. Create the omnibot user (if not already present)
sudo useradd -m -s /bin/bash omnibot || true
sudo usermod -aG sudo,omnibot,adm,dialout,cdrom,audio,video,plugdev,games,users,input,render,netdev,lpadmin,gpio,i2c,spi omnibot

# 4. Clone to /opt/omnibot (production path)
sudo mkdir -p /opt/omnibot
sudo git clone https://github.com/3D-Magic/OmniBot-Testing.git /opt/omnibot
# Or copy your local build to /opt/omnibot

# 5. Set ownership
sudo chown -R omnibot:omnibot /opt/omnibot

# 6. Install Python dependencies
cd /opt/omnibot
sudo pip3 install -r requirements.txt

# 7. Create systemd service for the backend
sudo tee /etc/systemd/system/omnibot.service << 'EOF'
[Unit]
Description=OMNIBOT
After=network.target

[Service]
Type=simple
User=omnibot
WorkingDirectory=/opt/omnibot/src
ExecStart=/usr/bin/python3 /opt/omnibot/src/app.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 8. Create kiosk service
sudo tee /etc/systemd/system/omnibot-kiosk.service << 'EOF'
[Unit]
Description=OMNIBOT Kiosk
After=omnibot.service

[Service]
Type=simple
User=omnibot
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser \
    --kiosk \
    --no-first-run \
    --no-default-browser-check \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-features=TranslateUI \
    --user-data-dir=/tmp/omnibot-chromium \
    http://localhost:8081/
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# 9. Enable auto-login via LightDM
sudo tee /etc/lightdm/lightdm.conf.d/10-omnibot.conf << 'EOF'
[Seat:*]
autologin-user=omnibot
autologin-user-timeout=0
EOF

# 10. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable omnibot omnibot-kiosk
sudo systemctl start omnibot

# 11. Reboot
sudo reboot
```

After reboot, the Pi will:
1. Auto-login as `omnibot` user via LightDM
2. Start the Flask backend on `0.0.0.0:8081`
3. Launch Chromium in kiosk mode pointing to `http://localhost:8081`

### System Tools to Use

| Tool | Purpose | Why |
|------|---------|-----|
| **NetworkManager (`nmcli`)** | WiFi management | Scan, connect, disconnect from the Settings page |
| **systemd** | Service management | `omnibot.service` runs the backend; `omnibot-kiosk.service` runs the display |
| **LightDM** | Display manager | Handles auto-login for the kiosk |
| **Chromium** | Kiosk browser | More stable than PyQt5 WebEngine on Pi |
| **journalctl** | Log viewing | `sudo journalctl -u omnibot -f` |

### Useful Commands

```bash
# View bot logs
sudo journalctl -u omnibot -f

# Restart the bot
sudo systemctl restart omnibot

# Restart kiosk display
sudo systemctl restart omnibot-kiosk

# Check WiFi status from terminal
nmcli dev wifi list

# Connect to WiFi from terminal
nmcli dev wifi connect "SSID" password "PASSWORD"

# Edit settings manually
sudo nano /opt/omnibot/config/settings.json
```

## 🔧 Commands

```bash
# Start the bot manually
python3 src/app.py

# View logs
sudo journalctl -u omnibot -f

# Check service status
sudo systemctl status omnibot

# Scan WiFi networks
nmcli dev wifi list

# Connect to WiFi
nmcli dev wifi connect "SSID" password "PASSWORD"
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
**Last Updated:** 2026-04-15
