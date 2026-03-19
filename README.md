# 🤖 OMNIBOT v2.6 Sentinel

**ML-Enhanced Automated Trading System for Raspberry Pi**

> **Zero Cost** • **Fully Automated** • **Open Source** • **Pi 5 Optimized**

---

## 🎯 What's New in v2.6 Sentinel

### Multi-Strategy Engine
- Run **4 strategies simultaneously** (Momentum, Mean Reversion, Breakout, ML Ensemble)
- Dynamic weight allocation based on performance
- Consensus-based signal generation

### Free Sentiment Analysis
- **Reddit** monitoring (r/wallstreetbets, r/stocks, r/investing)
- **RSS feeds** from Yahoo Finance, MarketWatch
- No paid APIs required

### Backtesting Engine
- Test strategies on historical data
- Walk-forward optimization
- Performance metrics (Sharpe ratio, max drawdown, win rate)

### Web Dashboard
- Real-time portfolio monitoring
- Mobile-responsive design
- Emergency stop button
- Strategy toggle controls

### Weekend Auto-Updates
- Automatically updates during market closures
- Built-in rollback on failure
- Zero manual intervention required

---

## 📋 Requirements

### Hardware
- **Raspberry Pi 5 (8GB recommended)** or Pi 4 (4GB minimum)
- MicroSD Card (32GB+, Class 10)
- Stable internet connection
- Power supply (5V 3A for Pi 5)

### Software
- Raspberry Pi OS (64-bit)
- Python 3.11+
- Git

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/3D-Magic/OmniBot.git
cd OmniBot
```

### 2. Run Setup
```bash
chmod +x setup.sh
./setup.sh
```

### 3. Configure API Keys
```bash
python src/main.py --setup
```

### 4. Start Trading
```bash
# Trading mode
python src/main.py --mode trading

# Or start dashboard
python src/main.py --mode dashboard
```

---

## 📊 Usage Modes

### Trading Mode
```bash
python src/main.py --mode trading
```
- Runs 24/7 automated trading
- Monitors watchlist
- Executes trades based on strategy signals
- Logs all activity

### Dashboard Mode
```bash
python src/main.py --mode dashboard
```
- Web interface at `http://your-pi-ip:8080`
- Real-time portfolio view
- Manual trade override
- Strategy controls

### Backtest Mode
```bash
python src/main.py --backtest --start 2023-01-01 --end 2024-01-01 --symbols AAPL,MSFT,GOOGL
```
- Test strategies on historical data
- Optimize parameters
- Generate performance reports

---

## 🧠 Strategies

### 1. Momentum Strategy
- Identifies trending stocks
- Uses 20-day lookback period
- Buy when momentum > 5%

### 2. Mean Reversion
- Finds overbought/oversold conditions
- Uses z-score calculation
- Buy when z-score < -2.0

### 3. Breakout Strategy
- Detects price breakouts
- Uses ATR for volatility
- Enters on confirmed breakouts

### 4. ML Ensemble
- LSTM-based predictions
- Combines technical indicators
- Adapts to market regimes

---

## ⚙️ Configuration

### Hardware Profiles
Automatically detected and optimized for:
- **Pi 5 8GB**: 4 parallel strategies, large ML models
- **Pi 4 8GB**: 2 parallel strategies, medium models
- **Pi 4 4GB**: 1 strategy, small models

### Trading Settings
Edit `config/settings.py`:
```python
TRADING = {
    "mode": "paper",        # paper or live
    "max_positions": 10,    # Max concurrent positions
    "risk_per_trade": 0.02, # 2% risk per trade
    "max_daily_loss": 0.05  # Stop after 5% daily loss
}
```

### Strategy Weights
Adjust in `config/settings.py`:
```python
STRATEGIES = {
    "momentum": {"enabled": True, "weight": 0.25},
    "mean_reversion": {"enabled": True, "weight": 0.25},
    "breakout": {"enabled": True, "weight": 0.25},
    "ml_ensemble": {"enabled": True, "weight": 0.25}
}
```

---

## 🔒 Security

- **File integrity verification**: Bot won't run if code is modified
- **Admin password**: Required for configuration changes
- **Encrypted config**: API keys are encrypted
- **Auto-lockout**: After 3 failed login attempts

---

## 📈 Performance

### Expected Metrics (Paper Trading)
- **Sharpe Ratio**: 1.2-1.8
- **Win Rate**: 55-65%
- **Max Drawdown**: <15%
- **Annual Return**: 15-25% (backtested)

### Resource Usage (Pi 5)
- **CPU**: 15-25% average
- **Memory**: 4-6GB
- **Network**: ~50MB/day
- **Disk**: ~100MB/week for logs

---

## 🆘 Troubleshooting

### Bot won't start
```bash
# Check logs
tail -f data/logs/omnibot_*.log

# Verify installation
python -c "import flask, pandas, yfinance; print('OK')"

# Reset config
rm config/user_config.py
python src/main.py --setup
```

### Dashboard not accessible
```bash
# Check if port 8080 is open
sudo ufw allow 8080

# Check service status
sudo systemctl status omnibot
```

### High memory usage
- Reduce `max_strategies` in settings
- Disable dashboard if not needed
- Clear cache: `rm -rf data/cache/*`

---

## 🤝 Contributing

This is a personal project. For feature requests or issues, please open a GitHub issue.

---

## ⚠️ Disclaimer

**Trading involves substantial risk of loss. This software is for educational purposes only.**

- Always start with **paper trading**
- Never trade more than you can afford to lose
- Past performance does not guarantee future results
- The authors are not responsible for any financial losses

---

## 📜 License

**Personal Use License**

- ✅ Use for your own trading
- ❌ No selling
- ❌ No modifications
- ❌ No redistribution
- ❌ No commercial use

---

## 🙏 Acknowledgments

- [yfinance](https://github.com/ranaroussi/yfinance) for free market data
- [Alpaca](https://alpaca.markets/) for commission-free trading
- [Flask](https://flask.palletsprojects.com/) for the web framework

---

**Made with ❤️ for the Raspberry Pi trading community**

*Version 2.6.0 - Sentinel*
