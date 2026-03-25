# 🤖 OmniBot v2.6.1 Sentinel

**ML-Enhanced Automated Trading System with Aggressive Trading Modes & Auto-Updates**

## 🚀 Quick Start

### Clone from GitHub (Correct Branch)
```bash
git clone -b V2.6.1-Omnibot_Sentinal https://github.com/3D-Magic/OmniBot-Testing.git OmniBot-v2.6.1
cd OmniBot-v2.6.1
chmod +x scripts/omnibot.sh
pip3 install -r requirements.txt --break-system-packages
./scripts/omnibot.sh start
```

### Update Existing Installation
```bash
cd ~/OmniBot-v2.6.1
git pull origin V2.6.1-Omnibot_Sentinal
./scripts/omnibot.sh restart
```

## 🛠️ Commands

| Command | Description |
|---------|-------------|
| `./omnibot.sh start` | Start bot with ngrok |
| `./omnibot.sh stop` | Stop bot |
| `./omnibot.sh restart` | Restart bot |
| `./omnibot.sh url` | Get current ngrok URL |
| `./omnibot.sh status` | Check if running |

## 📊 Features

- **Trading Modes**: Conservative, Moderate, Aggressive, HFT Scalper, Sentinel
- **Auto-Update**: Weekend automatic updates
- **Dashboard**: Web interface with mode selector
- **Update/Restart Buttons**: One-click operations
- **API Endpoints**: /api/positions, /api/portfolio, /api/strategies, /api/system, /api/history

## 📜 License

Personal Use License
