# 🤖 OmniBot v2.6.1 Sentinel

**ML-Enhanced Automated Trading System**

## 🚀 Quick Start

### Clone from GitHub (Correct Branch)
```bash
git clone -b V2.6.1-Omnibot_Sentinal https://github.com/3D-Magic/OmniBot-Testing.git OmniBot-v2.6.1
cd OmniBot-v2.6.1
chmod +x scripts/omnibot.sh
./scripts/omnibot.sh start --ngrok
```

### Update Existing Installation
```bash
cd ~/OmniBot-v2.6.1
git pull origin V2.6.1-Omnibot_Sentinal
./scripts/omnibot.sh restart --ngrok
```

## 🛠️ Commands

| Command | Description |
|---------|-------------|
| `./omnibot.sh start` | Start bot with ngrok |
| `./omnibot.sh stop` | Stop bot |
| `./omnibot.sh restart` | Restart bot |
| `./omnibot.sh url` | Get current ngrok URL |
| `./omnibot.sh status` | Check if running |

## 📊 Dashboard Features

- Trading modes: Conservative, Moderate, Aggressive, HFT, Sentinel
- Update & restart buttons
- Auto-update on weekends
- Portfolio tracking
- Strategy monitoring

## 🔧 Requirements

```bash
pip3 install flask flask-cors --break-system-packages
```

## 📜 License

MIT License
