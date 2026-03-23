# 🤖 OmniBot v2.6 Sentinel Enhanced

**ML-Enhanced Automated Trading System with Aggressive Trading Modes & Auto-Updates**

Optimized for Raspberry Pi • Zero Cost • Open Source

---

## ✨ What's New in Enhanced

### 🎛️ 5 Trading Modes (Fixes "Not Trading" Issues)
| Mode | Confidence | Risk/Trade | Frequency | Use Case |
|------|-----------|------------|-----------|----------|
| **Conservative** | 75%+ | 2% | Low | Capital preservation |
| **Moderate** | 65%+ | 5% | Medium | Balanced growth |
| **Aggressive** | 55%+ | 10% | **High** | **Active trading** |
| **HFT Scalper** | 48%+ | 5% | Very High | Short-term scalping |
| **Sentinel** | N/A | N/A | None | Monitor-only |

### 🔄 Auto-Update System
- ✅ **Manual**: "Check for Updates" button in dashboard
- ✅ **Automatic**: Checks every 24 hours
- ✅ **Weekend Updates**: Applies when market closed (no manual steps)
- ✅ **Safe Restart**: Preserves config, auto-restarts dashboard

---

## 🚀 Quick Start

```bash
# Install
chmod +x setup.sh
./setup.sh

# Start with aggressive mode
./scripts/omnibot.sh start --ngrok
```

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
