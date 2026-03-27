# 🤖 OMNIBOT v2.7 Titan



> **Stocks** • **Crypto** • **Forex** | Always Accessible | Based on v2.6.1 Sentinel




**Multi-Market Automated Trading System | 24/7 Remote Access**

![OmniBot Diagram](https://kimi-web-img.moonshot.cn/img/raw.githubusercontent.com/3D-Magic/OmniBot-Testing/main/docs/diagram.png)

> **Stocks** • **Crypto** • **Forex** | Always Accessible | Based on v2.6.1 Sentinel

---

## 🚀 First Time Setup (Fresh Install)

For new installations on a clean SD card or fresh OS:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install required packages
sudo apt install -y git python3 python3-pip python3-venv

# 3. Clone the repository
git clone https://github.com/3D-Magic/OmniBot-Testing.git

# 4. Enter the directory
cd OmniBot-Testing

# 5. Run setup (with unbuffered flag for Putty)
python3 -u src/main.py --setup
```

**Note for Putty users:** The `-u` flag forces unbuffered output, preventing terminal freezes during interactive setup.

---

## 🚀 Quick Start (Already Cloned)

If you've already cloned the repository:

```bash
# Run automated setup
chmod +x setup.sh
./setup.sh

# Or run interactive setup wizard directly
python3 -u src/main.py --setup

# Start trading
./scripts/omnibot.sh start
```

---

## 🌍 24/7 Remote Access (No Port Forwarding!)

### 🥇 Tailscale (Recommended - FREE)
- Static IP (never changes)
- Full network access (SSH, dashboard, files)
- Works even if your home IP changes
- Free for personal use

```bash
# Install
./scripts/omnibot.sh install-tailscale

# Or manually
curl -fsSL https://tailscale.com/install.sh | sudo bash
sudo tailscale up

# Access from anywhere
http://your-pc-name:8081
```

### 🥈 Cloudflare Tunnel (Most Professional - FREE)
- Custom domain support
- Most reliable uptime
- Requires domain name

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Setup
cloudflared tunnel login
cloudflared tunnel create omnibot
cloudflared tunnel route dns omnibot yourdomain.com
cloudflared tunnel run omnibot
```

### 🥉 ngrok (Easiest - FREE tier)
- Easiest setup
- URL changes on restart (free tier)

```bash
# Sign up: https://dashboard.ngrok.com
# Get authtoken and configure

# Start with ngrok
./scripts/omnibot.sh start
# URL shown in terminal
```

### 4️⃣ localhost.run (No Signup - FREE)
```bash
ssh -R 80:localhost:8081 localhost.run
```

---

## 📊 Multi-Market Trading

| Market | Provider | Status | Setup Time |
|--------|----------|--------|------------|
| US Stocks | Alpaca | Ready | 5 min |
| Crypto | Binance/Coinbase/Kraken | Ready | 5 min |
| Forex | OANDA | Ready | 5 min |
| Options | Alpaca | Beta | 5 min |

### Market Hours
- **Stocks:** Mon-Fri 9:30AM-4PM EST
- **Crypto:** 24/7/365
- **Forex:** Sun 5PM - Fri 5PM EST

---

## 🎮 Trading Modes (from v2.6.1)

| Mode | Risk | Max Pos | Leverage | Best For |
|------|------|---------|----------|----------|
| Conservative | 1% | 5 | 1x | Beginners |
| Moderate | 2% | 10 | 1x | Most users |
| Aggressive | 5% | 15 | 2x | Experienced |
| HFT Scalper | 2% | 20 | 3x | High frequency |
| Sentinel | 2.5% | 12 | 1.5x | AI-enhanced |

---

## 🛠️ Commands

### Bot Control
```bash
./scripts/omnibot.sh start              # Start with configured tunnel
./scripts/omnibot.sh stop               # Stop bot
./scripts/omnibot.sh restart            # Restart bot
./scripts/omnibot.sh status             # Check status & URLs
./scripts/omnibot.sh url                # Get remote access URL
./scripts/omnibot.sh logs               # View real-time logs
./scripts/omnibot.sh install-tailscale  # Install Tailscale
```

### Setup & Configuration
```bash
python3 src/main.py --setup              # Interactive setup wizard
python3 src/main.py --api-links          # Show API signup URLs
python3 src/main.py --trading-modes      # View trading modes
python3 src/main.py --tunnel-options     # Show remote access options
python3 src/main.py --api-status         # Check API configuration
python3 src/main.py --change-password    # Change dashboard password
python3 src/main.py --install-tailscale  # Install Tailscale
```

---

## 🔗 API Signup Links

| Service | URL | Cost |
|---------|-----|------|
| Alpaca (Stocks) | https://alpaca.markets | FREE |
| Binance (Crypto) | https://binance.com | FREE (testnet) |
| OANDA (Forex) | https://oanda.com/demo-account | FREE |
| Tailscale | https://login.tailscale.com/start | FREE |
| Cloudflare | https://dash.cloudflare.com/sign-up | FREE |
| ngrok | https://dashboard.ngrok.com/signup | FREE tier |

---

## 🎨 Dashboard Features

- Total Capital Display with profit % badge (top right)
- Multi-Market Tabs (Stocks/Crypto/Forex/All)
- Time Period Cards (Week/Month/Year/All Time)
- Circular Progress Gauges with win/loss stats
- Real-time Charts (Account Balance, R:R)
- Trade History with P&L indicators
- Monthly Performance Grid
- Dark Professional Theme

---

## 🆘 Troubleshooting

### Putty Freezing During Setup
Use unbuffered mode: `python3 -u src/main.py --setup`

### Port 8081 in use
```bash
./scripts/omnibot.sh stop
pkill -9 -f "python3 src/main.py"
```

### Tailscale not connecting
```bash
sudo tailscale up
# Authenticate in browser
```

### Missing dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### File not found errors
Ensure you're in the OmniBot-Testing directory:
```bash
cd ~/OmniBot-Testing
pwd  # Should show /home/biqu/OmniBot-Testing or similar
```

---

## 📜 License

Personal Use License
```
