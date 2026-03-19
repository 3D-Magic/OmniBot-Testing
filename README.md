# 🤖 OMNIBOT v2.6 Sentinel

ML-Enhanced Automated Trading System optimized for Raspberry Pi Zero Cost / Open Source.

## 🚀 Quick Start

```bash
# Download and install
cd ~
wget https://github.com/3D-Magic/OmniBot-Testing/archive/refs/heads/main.zip -O omnibot-v2.6.zip
unzip omnibot-v2.6.zip
mv OmniBot-Testing-main OmniBot-v2.6
cd OmniBot-v2.6

# Run setup
chmod +x setup.sh
./setup.sh

# Start with external access
./scripts/omnibot.sh start --ngrok
```

## 🌐 External Access (ngrok)

1. Get free token at https://dashboard.ngrok.com
2. Run setup: `python src/main.py --setup`
3. Enter ngrok token
4. Start: `./scripts/omnibot.sh start --ngrok`

## 📁 Structure

```
omnibot-v2.6/
├── src/
│   ├── main.py                 # Entry point
│   ├── core/                   # Trading engine, data fetcher, auto-updater
│   ├── strategies/             # Trading strategies
│   ├── sentiment/              # Sentiment analysis
│   ├── backtest/               # Backtesting engine
│   └── dashboard/              # Web dashboard
├── config/settings.py          # Configuration
├── scripts/omnibot.sh          # Helper script
├── setup.sh                    # Installation
└── clean-install.sh            # Clean reinstall
```

## 🛠️ Commands

```bash
# Start dashboard with ngrok
./scripts/omnibot.sh start --ngrok

# Check status
./scripts/omnibot.sh status

# Attach to running session
tmux attach -t omnibot

# Stop
./scripts/omnibot.sh stop

# Restart
./scripts/omnibot.sh restart --ngrok
```

## 🔧 Fixes in v2.6

- ✅ Fixed `Dict` import in auto_updater.py
- ✅ Fixed `allow_unsafe_werkzeug` for ngrok
- ✅ Fixed `auth_required` key in dashboard
- ✅ Removed tensorflow-lite (Python 3.13 compatibility)
- ✅ Added full ngrok integration
- ✅ Added terminal keep-alive via tmux
- ✅ Added helper scripts

## 📝 Notes

- Default dashboard port: 8081
- Default password: `admin`
- Tested on Raspberry Pi 5 with Python 3.13
- Uses scikit-learn instead of TensorFlow for ML (better Pi compatibility)

## 📜 License

MIT License - Open Source
