# 🤖 OmniBot v2.6.1 Sentinel Enhanced

**ML-Enhanced Automated Trading System with Aggressive Trading Modes & Auto-Updates**

Optimized for Raspberry Pi • Zero Cost • Open Source

---

## 🚀 Quick Start

### Option 1: Clone from GitHub (Recommended)
```bash
# Clone the repository
git clone https://github.com/3D-Magic/OmniBot-Testing.git OmniBot-v2.6.1
cd OmniBot-v2.6.1

# Run setup
chmod +x setup.sh
./setup.sh

# Start with aggressive mode
./scripts/omnibot.sh start --ngrok
```

### Option 2: Download and Extract
```bash
# Download latest release
wget https://github.com/3D-Magic/OmniBot-Testing/archive/refs/heads/main.zip -O omnibot-v2.6.zip
unzip omnibot-v2.6.zip
mv OmniBot-Testing-main OmniBot-v2.6.1
cd OmniBot-v2.6.1

# Run setup
chmod +x setup.sh
./setup.sh

# Start with aggressive mode
./scripts/omnibot.sh start --ngrok
```

### Option 3: Update Existing Installation
```bash
cd ~/OmniBot-v2.6.1
git pull origin main
./scripts/omnibot.sh restart --ngrok
```

---

## ✨ What's New in Enhanced

### 🎛️ 5 Trading Modes (Fixes "Not Trading" Issues)
| Mode | Confidence | Risk/Trade | Frequency | Use Case |
|------|-----------|------------|-----------|----------|
| **Conservative** | 75%+ | 2% | Low | Capital preservation |
| **Moderate** | 65%+ | 5% | Medium | Balanced growth |
| **Aggressive** | 55%+ | 10% | **High** | **Active trading** |
| **HFT Scalper** | 48%+ | 5% | Very High | **Scalping** |
| **Sentinel** | N/A | N/A | None | Monitor-only |

### 🔄 Auto-Update System
- ✅ **Manual**: "Check for Updates" button in dashboard
- ✅ **Automatic**: Checks every 24 hours
- ✅ **Weekend Updates**: Applies when market closed (no manual steps)
- ✅ **Safe Restart**: Preserves config, auto-restarts dashboard

---

## 🛠️ Commands

```bash
./scripts/omnibot.sh start --ngrok    # Start with external access
./scripts/omnibot.sh stop             # Stop bot
./scripts/omnibot.sh restart --ngrok  # Restart
./scripts/omnibot.sh status           # Check status
./scripts/omnibot.sh update           # Check for updates
```

---

## 📜 License

MIT License - Open Source
