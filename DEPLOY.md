# OMNIBOT v2.7 Titan - Deployment Guide

## Quick Deploy (Recommended)

### Step 1: Copy to Raspberry Pi
```bash
# On your computer, copy the omnibot_modular folder to the Pi
scp -r omnibot_modular/* omnibot@192.168.1.207:/tmp/omnibot_new/
```

### Step 2: Run Installer on Pi
```bash
# SSH to the Pi
ssh omnibot@192.168.1.207

# Run the installer
cd /tmp/omnibot_new
sudo ./install.sh

# The installer will:
# - Stop existing service
# - Copy files to /opt/omnibot
# - Create virtual environment
# - Install dependencies
# - Create systemd service
# - Start the service
```

### Step 3: Access Dashboard
```
http://192.168.1.207:8081
Login: admin / admin
```

## Manual Deploy (If install.sh fails)

```bash
# 1. Stop existing service
sudo systemctl stop omnibot-dashboard

# 2. Backup old version
sudo mv /opt/omnibot /opt/omnibot.backup.$(date +%Y%m%d)

# 3. Create new directory
sudo mkdir -p /opt/omnibot
sudo mkdir -p /etc/omnibot

# 4. Copy files
sudo cp -r /tmp/omnibot_new/* /opt/omnibot/

# 5. Create virtual environment
sudo python3 -m venv /opt/omnibot/venv

# 6. Install dependencies
sudo /opt/omnibot/venv/bin/pip install flask flask-socketio flask-session
sudo /opt/omnibot/venv/bin/pip install alpaca-py python-binance ib-insync

# 7. Create session directory
sudo mkdir -p /tmp/flask_session
sudo chmod 755 /tmp/flask_session

# 8. Create settings file (if doesn't exist)
if [ ! -f /etc/omnibot/settings.json ]; then
    sudo tee /etc/omnibot/settings.json > /dev/null << 'EOF'
{
  "version": "v2.7.2-titan",
  "password": "admin",
  "trading_mode": "demo",
  "strategy": "moderate"
}
EOF
fi

# 9. Fix permissions
sudo chown -R omnibot:omnibot /opt/omnibot
sudo chown -R omnibot:omnibot /etc/omnibot
sudo chmod 600 /etc/omnibot/settings.json

# 10. Create systemd service
sudo tee /etc/systemd/system/omnibot-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=OMNIBOT v2.7 Titan Trading Dashboard
After=network.target

[Service]
Type=simple
User=omnibot
WorkingDirectory=/opt/omnibot
Environment=PATH=/opt/omnibot/venv/bin
Environment=PYTHONPATH=/opt/omnibot
ExecStart=/opt/omnibot/venv/bin/python /opt/omnibot/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 11. Start service
sudo systemctl daemon-reload
sudo systemctl enable omnibot-dashboard
sudo systemctl start omnibot-dashboard

# 12. Check status
sudo systemctl status omnibot-dashboard
sudo journalctl -u omnibot-dashboard -f
```

## Post-Deploy Configuration

### 1. Configure Alpaca
1. Go to Settings page
2. Enter Alpaca API Key and Secret
3. Click "Test Connection"
4. If connected, balance will show on dashboard

### 2. Configure Binance
1. Get testnet keys from: https://testnet.binance.vision
2. Enter keys in Settings
3. Click "Test Connection"

### 3. Configure IB Gateway (optional)
1. Install IB Gateway on Pi
2. Enter account credentials in Settings
3. Click "Test Connection"

### 4. Change Password
```python
# On the Pi:
python3 << 'EOF'
import sys
sys.path.insert(0, '/opt/omnibot')
from config import Settings
s = Settings()
s.change_password('your_new_password')
print('Password changed!')
EOF
```

## Troubleshooting

### Login Not Working
```bash
# Clear session cache
sudo rm -rf /tmp/flask_session/*
sudo systemctl restart omnibot-dashboard
```

### Dashboard Shows $0.00
```bash
# Check if brokers are configured
cat /etc/omnibot/settings.json | grep -E "(alpaca_key|binance_key)"

# Check logs
sudo journalctl -u omnibot-dashboard -n 50
```

### Service Won't Start
```bash
# Check for errors
sudo journalctl -u omnibot-dashboard -n 100

# Test manually
sudo /opt/omnibot/venv/bin/python /opt/omnibot/app.py
```

### Permission Denied
```bash
sudo chown -R omnibot:omnibot /opt/omnibot
sudo chown -R omnibot:omnibot /etc/omnibot
sudo chmod 755 /tmp/flask_session
```

## Verification

After deployment, run the verification script:
```bash
cd /opt/omnibot
sudo /opt/omnibot/venv/bin/python verify.py
```

All tests should pass.
