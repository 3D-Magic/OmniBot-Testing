# OmniBot v2.7.3 Titan AI — Autonomous Trading Bot

> **AI-Powered, Multi-Broker, Touchscreen-Ready Trading Bot for Raspberry Pi**
>
> Runs 24/7 on a Pi with a DSI touchscreen, connects to Alpaca (stocks) and Binance (crypto), and makes autonomous trade decisions using real technical indicators + ensemble scoring.

---

## What It Does

OmniBot is a fully autonomous trading bot that:

- **Scans** multiple symbols across Alpaca (US equities) and Binance (crypto) every 30 seconds
- **Analyzes** price action using SMA/EMA crossovers, RSI, MACD, Bollinger Bands, volume analysis, and pattern recognition
- **Scores** each symbol with a weighted ensemble model and generates buy/sell signals
- **Executes** trades automatically through your broker with fee-aware position sizing
- **Displays** everything on a touchscreen dashboard running in a Chromium kiosk

---

## Key Features

| Feature | Description |
|---------|-------------|
| **AI Trading Engine** | Ensemble scoring using 5 indicator categories: trend, momentum, volatility, volume, pattern |
| **Multi-Broker** | Alpaca (paper/live stocks) + Binance (spot crypto) + extensible for IBKR |
| **Fee-Aware Sizing** | Calculates breakeven after fees before placing any order |
| **Free Data Fallback** | Alpaca bars fall back to **Yahoo Finance** when market is closed — no API key needed |
| **Market Hours Awareness** | Skips stock scanning when US market is closed; still accumulates historical bars |
| **Touchscreen Dashboard** | 800x480 DSI touchscreen with touch keyboard, scrollable UI, real-time status |
| **Persistent Trade Log** | Every trade attempt logged to `/opt/omnibot/logs/trades.jsonl` |
| **IP Ban Protection** | Thread-safe + file-based cooldowns to prevent API rate-limit bans |
| **Auto-Connect** | Brokers auto-reconnect on disconnection with exponential backoff |
| **Risk Management** | Stop-loss, take-profit, max position %, max daily loss limits |

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Raspberry Pi 4/5              │
│  ┌─────────────────────────────────┐    │
│  │    Chromium Kiosk (800x480)     │    │
│  │    Touch Keyboard + Dashboard   │    │
│  └─────────────────────────────────┘    │
│                 │                        │
│  ┌──────────────▼──────────────┐        │
│  │      Flask App (8081)       │        │
│  │  - Dashboard API            │        │
│  │  - Settings management      │        │
│  └──────────────┬──────────────┘        │
│                 │                        │
│  ┌──────────────▼──────────────┐        │
│  │    AI Trading Engine        │        │
│  │  - Price history (200 bars) │        │
│  │  - Technical indicators     │        │
│  │  - Signal scoring           │        │
│  │  - Order execution          │        │
│  └──────────────┬──────────────┘        │
│                 │                        │
│  ┌──────────────▼──────────────┐        │
│  │    Balance Aggregator       │        │
│  │  - Alpaca (paper/live)      │        │
│  │  - Binance (mainnet)        │        │
│  │  - Yahoo Finance fallback   │        │
│  └─────────────────────────────┘        │
└─────────────────────────────────────────┘
```

---

## Screenshots

*(Add your own screenshots of the dashboard here)*

- Login page with touch keyboard
- Main dashboard showing portfolio, positions, AI status
- Settings page for broker configuration
- Trade log viewer

---

## Hardware Requirements

| Component | Recommendation |
|-----------|---------------|
| **Board** | Raspberry Pi 4 (4GB+) or Pi 5 |
| **Screen** | 800x480 DSI touchscreen (WaveShare or similar) |
| **Storage** | 32GB+ microSD |
| **Network** | WiFi or Ethernet (stable connection required) |
| **OS** | Raspberry Pi OS (64-bit recommended) |

---

## Software Setup

### 1. Install OS & Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git python3 python3-pip python3-venv \
    chromium-browser unclutter matchbox-keyboard \
    libatlas-base-dev libffi-dev libssl-dev

# Enable DSI display (if not already)
sudo raspi-config
# -> Display Options -> DSI Display -> Enable
```

### 2. Clone & Install

```bash
cd /opt
sudo git clone https://github.com/yourusername/omnibot.git
sudo chown -R $USER:$USER /opt/omnibot
cd /opt/omnibot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install yfinance (free data fallback)
pip install yfinance
```

### 3. Configure Brokers

Edit `config/settings.json`:

```json
{
  "trading_enabled": true,
  "trading_mode": "paper",
  "strategy": "swing_trading",
  "alpaca": {
    "api_key": "YOUR_ALPACA_KEY",
    "secret_key": "YOUR_ALPACA_SECRET",
    "paper": true
  },
  "binance": {
    "api_key": "YOUR_BINANCE_KEY",
    "secret_key": "YOUR_BINANCE_SECRET",
    "testnet": false,
    "enabled": true
  },
  "alpaca_watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"],
  "binance_watchlist": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
}
```

> **Note**: Set `binance.testnet: true` for paper trading on Binance testnet. Set to `false` for real trading on mainnet.

### 4. Install System Service

```bash
sudo cp scripts/omnibot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable omnibot.service
sudo systemctl start omnibot.service
```

### 5. Configure Kiosk Mode (Touchscreen)

```bash
# Install kiosk autostart
cp scripts/kiosk.desktop ~/.config/autostart/

# Or manually create:
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/omnibot-kiosk.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=OmniBot Kiosk
Exec=/usr/bin/chromium-browser --kiosk --noerrdialogs --disable-infobars \
  --app=http://localhost:8081 --check-for-update-interval=31536000
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

### 6. Reboot

```bash
sudo reboot
```

The Pi will boot straight into the OmniBot dashboard in kiosk mode.

---

## Configuration

### Settings File (`config/settings.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `trading_enabled` | `true` | Master switch for trading |
| `trading_mode` | `"paper"` | `"paper"` or `"live"` |
| `strategy` | `"swing_trading"` | Maps to AI strategy (conservative/moderate/aggressive/adaptive) |
| `stop_loss_pct` | `5` | Stop loss percentage |
| `take_profit_pct` | `10` | Take profit percentage |
| `max_position_pct` | `10` | Max % of portfolio per position |
| `alpaca.paper` | `true` | Alpaca paper trading mode |
| `binance.testnet` | `false` | Binance testnet (true) or mainnet (false) |

### AI Strategy Modes

| Strategy | Threshold | Behavior |
|----------|-----------|----------|
| `conservative` | 0.75 | Only trades on very strong signals, smaller positions |
| `moderate` | 0.50 | Balanced approach (default) |
| `aggressive` | 0.30 | Trades on weaker signals, larger positions |
| `adaptive` | Dynamic | Adjusts threshold based on recent trade performance |

---

## How Trading Works

### 1. Price History Accumulation

```
Every 60 seconds per symbol:
  - Alpaca: tries Alpaca API → falls back to Yahoo Finance
  - Binance: uses Binance mainnet data client
  
First fetch: loads 30 historical bars
Subsequent: appends only new bars (deduplication)
```

### 2. AI Analysis (every 30 seconds)

```
For each symbol with 30+ bars:
  1. Calculate features:
     - SMA/EMA ratios, crossovers
     - RSI (14-period)
     - MACD histogram
     - Bollinger Band position & width
     - Volume ratio vs SMA
     - Price patterns (consecutive moves, double tops/bottoms)
  
  2. Score each category (-1 to +1):
     - Trend: 25% weight
     - Momentum: 25% weight
     - Volatility: 20% weight
     - Volume: 15% weight
     - Pattern: 15% weight
  
  3. Weighted ensemble score → confidence (0-1)
  
  4. If confidence >= threshold AND side is clear:
     → Execute trade
```

### 3. Trade Execution

```
1. Get latest price
2. Calculate position size (% of portfolio × confidence)
3. Estimate fees (Alpaca: $0.01 min, Binance: 0.1%)
4. Fee check: breakeven must be < 50% of expected profit
5. Submit market order
6. Log to trades.jsonl
7. Track position for stop-loss / take-profit
```

---

## Dashboard

Access the dashboard at `http://<pi-ip>:8081`

Default login:
- **Password**: `admin` (change in `config/settings.json`)

### Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Portfolio summary, AI status, broker connections |
| Positions | `/positions` | Current open positions |
| Orders | `/orders` | Order history |
| Settings | `/settings` | Broker config, strategy, risk limits |
| Trade Log | `/logs` | View trades.jsonl |
| Scan | `/scan` | Manual symbol scan |

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Full system status (portfolio, brokers, engine) |
| `POST /api/toggle_trading` | Enable/disable trading |
| `POST /api/sell_all` | Liquidate all positions |
| `GET /api/fee_estimate` | Estimate fees for a trade |

---

## File Structure

```
omnibot/
├── app.py                      # Flask app factory
├── requirements.txt            # Python dependencies
├── config/
│   ├── settings.json           # Live configuration
│   ├── settings.py             # Settings loader
│   └── ai_model.pkl            # Saved ML model (optional)
├── brokers/
│   ├── alpaca_config.py        # Alpaca broker (paper/live)
│   ├── binance_config.py       # Binance broker (testnet/mainnet)
│   ├── yfinance_client.py      # Free Yahoo Finance fallback
│   ├── balance_aggregator.py   # Portfolio summary aggregator
│   └── base_broker.py          # Abstract base class
├── engine/
│   ├── ai_trading_engine.py    # Core AI engine
│   ├── trading_engine.py       # Legacy engine
│   └── strategies.py           # Strategy mappings
├── templates/                  # Jinja2 HTML templates
├── static/                     # CSS, JS assets
├── logs/
│   └── trades.jsonl            # Persistent trade log
├── scripts/
│   ├── install.sh              # Installation script
│   └── omnibot.service         # systemd service file
└── src/
    ├── dashboard/              # Dashboard routes
    └── system/                 # Screen/WiFi managers
```

---

## Troubleshooting

### Bot not trading?

Check logs:
```bash
sudo journalctl -u omnibot.service -f
```

Common causes:
- **Alpaca**: US market closed (09:30–16:00 ET Mon–Fri). Yahoo Finance provides historical bars 24/7.
- **Binance**: IP banned → check cooldown messages. File-based cooldown resets on restart.
- **Threshold too high**: Lower `confidence_threshold` in settings or use `aggressive` strategy.
- **Insufficient bars**: Need 30 × 5-min bars = 2.5 hours of data. First fetch loads history.

### Binance IP banned?

The bot has a 5-minute file-based cooldown. If still banned:
```bash
# Clear cooldown file
sudo rm /tmp/omnibot_binance_cooldown
sudo systemctl restart omnibot.service
```

### Touch keyboard not working?

The dashboard injects an inline touch keyboard. If it doesn't appear:
- Tap any text input field
- The keyboard slides up from the bottom
- Supports SHIFT, DEL, ENTER, and character keys

### Screen not rotating / brightness errors?

The screen manager tries `xrandr` and `xset` which may not be installed on headless Pi. These are cosmetic warnings.

### Reset everything?

```bash
sudo systemctl stop omnibot.service
sudo rm -f /opt/omnibot/logs/trades.jsonl
sudo rm -f /tmp/omnibot_binance_cooldown
sudo systemctl start omnibot.service
```

---

## Safety & Warnings

> ⚠️ **This is algorithmic trading software. Use at your own risk.**
>
> - Always start with **paper trading** (`paper: true`)
> - Test thoroughly before going live
> - The AI makes decisions based on technical indicators — it can and will lose money
> - Past performance does not guarantee future results
> - Crypto markets are highly volatile
> - Set stop-losses and position limits appropriate for your risk tolerance

---

## License

MIT License — see `LICENSE` file.

---

## Credits

- **Alpaca Markets** — Commission-free stock trading API
- **Binance** — Crypto exchange API
- **Yahoo Finance** — Free historical market data via `yfinance`
- **Flask** — Web framework
- **scikit-learn** — ML model support

---

## Changelog

### v2.7.3 Titan AI
- Added Yahoo Finance fallback for Alpaca historical data (free, no API key)
- Added US market-hours awareness — skips stock scanning when market closed
- Added persistent trade logging (`trades.jsonl`)
- Added file-based Binance cooldown (survives restarts)
- Lowered default AI threshold from 0.50 → 0.30
- Added raw AI score logging for debugging
- Fixed touch keyboard for DSI touchscreen
- Fixed scrollbar visibility for touchscreen drag-to-scroll
- Removed duplicate Chromium kiosk windows

### v2.7.2
- AI Trading Engine with ensemble scoring
- Multi-broker support (Alpaca + Binance)
- Fee-aware position sizing
- Touchscreen dashboard with inline keyboard
- systemd service for 24/7 operation

---

**Questions? Issues?** Open a GitHub issue or check the logs with `sudo journalctl -u omnibot.service -f`.
