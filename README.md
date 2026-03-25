# 🤖 OmniBot v2.6.1 Sentinel Enhanced

**ML-Enhanced Automated Trading System with Aggressive Trading Modes & Auto-Updates**

---

## 🚀 Quick Start

### Clone from GitHub (Correct Branch)
```bash
# Clone the correct branch
git clone -b V2.6.1-Omnibot_Sentinal https://github.com/3D-Magic/OmniBot-Testing.git OmniBot-v2.6.1
cd OmniBot-v2.6.1

# Fix permissions
chmod +x scripts/omnibot.sh setup.sh

# Run setup
./setup.sh

# Start with aggressive mode
./scripts/omnibot.sh start --ngrok
```

### Update Existing Installation
```bash
cd ~/OmniBot-v2.6.1
git pull origin V2.6.1-Omnibot_Sentinal
chmod +x scripts/omnibot.sh
./scripts/omnibot.sh restart --ngrok
```

---

## 🛠️ Troubleshooting

### "couldn't find remote ref main"
Use the correct branch name:
```bash
git pull origin V2.6.1-Omnibot_Sentinal
```

### "Permission denied"
Fix script permissions:
```bash
chmod +x scripts/omnibot.sh
chmod +x setup.sh
```

### Fresh Install
```bash
cd ~
rm -rf OmniBot-v2.6.1
git clone -b V2.6.1-Omnibot_Sentinal https://github.com/3D-Magic/OmniBot-Testing.git OmniBot-v2.6.1
cd OmniBot-v2.6.1
chmod +x scripts/omnibot.sh setup.sh
./setup.sh
./scripts/omnibot.sh start --ngrok
```

---

## 🎛️ Trading Modes

| Mode | Confidence | Risk/Trade | Frequency | Use Case |
|------|-----------|------------|-----------|----------|
| **Conservative** | 75%+ | 2% | Low | Capital preservation |
| **Moderate** | 65%+ | 5% | Medium | Balanced growth |
| **Aggressive** | 55%+ | 10% | **High** | **Active trading** |
| **HFT Scalper** | 48%+ | 5% | Very High | **Scalping** |
| **Sentinel** | N/A | N/A | None | Monitor-only |

---

## 📜 License

MIT License - Open Source
