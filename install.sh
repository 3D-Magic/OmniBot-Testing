#!/bin/bash
# OMNIBOT v2.7 Titan - Modular Edition Installation Script
# Run this after cloning from GitHub

set -e

echo "=========================================="
echo "OMNIBOT v2.7 Titan - Modular Installer"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [[ $(uname -m) != "aarch64" && $(uname -m) != "armv7l" ]]; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Configuration
INSTALL_DIR="/opt/omnibot"
VENV_DIR="$INSTALL_DIR/venv"
SETTINGS_DIR="/etc/omnibot"
SERVICE_NAME="omnibot-dashboard"

# Check if running as root for some operations
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Some operations require sudo privileges${NC}"
    SUDO="sudo"
else
    SUDO=""
fi

echo "[1/8] Stopping existing service..."
$SUDO systemctl stop $SERVICE_NAME 2>/dev/null || true
$SUDO systemctl disable $SERVICE_NAME 2>/dev/null || true

echo "[2/8] Creating directories..."
$SUDO mkdir -p $INSTALL_DIR
$SUDO mkdir -p $SETTINGS_DIR
$SUDO mkdir -p $INSTALL_DIR/templates
$SUDO mkdir -p $INSTALL_DIR/static/css
$SUDO mkdir -p $INSTALL_DIR/static/js
$SUDO mkdir -p /tmp/flask_session

echo "[3/8] Copying files..."
# Copy modular code
$SUDO cp -r config brokers engine visualization wifi $INSTALL_DIR/
$SUDO cp app.py requirements.txt $INSTALL_DIR/
$SUDO cp templates/* $INSTALL_DIR/templates/ 2>/dev/null || true
$SUDO cp static/css/* $INSTALL_DIR/static/css/ 2>/dev/null || true
$SUDO cp static/js/* $INSTALL_DIR/static/js/ 2>/dev/null || true

# Copy __init__.py files
$SUDO cp __init__.py $INSTALL_DIR/
$SUDO touch $INSTALL_DIR/config/__init__.py
$SUDO touch $INSTALL_DIR/brokers/__init__.py
$SUDO touch $INSTALL_DIR/engine/__init__.py
$SUDO touch $INSTALL_DIR/visualization/__init__.py
$SUDO touch $INSTALL_DIR/wifi/__init__.py

echo "[4/8] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    $SUDO python3 -m venv $VENV_DIR
fi

# Install requirements
echo "[5/8] Installing Python packages..."
$SUDO $VENV_DIR/bin/pip install --upgrade pip
$SUDO $VENV_DIR/bin/pip install -r $INSTALL_DIR/requirements.txt

echo "[6/8] Creating default settings..."
if [ ! -f "$SETTINGS_DIR/settings.json" ]; then
    $SUDO tee $SETTINGS_DIR/settings.json > /dev/null << 'EOF'
{
  "version": "v2.7.2-titan",
  "password": "admin",
  "trading_mode": "demo",
  "strategy": "moderate",
  "alpaca_key": "",
  "alpaca_secret": "",
  "binance_key": "",
  "binance_secret": "",
  "trading_enabled": false
}
EOF
    echo -e "${GREEN}Created default settings (password: admin)${NC}"
fi

# Set permissions
$SUDO chown -R omnibot:omnibot $INSTALL_DIR 2>/dev/null || $SUDO chown -R root:root $INSTALL_DIR
$SUDO chown -R omnibot:omnibot $SETTINGS_DIR 2>/dev/null || $SUDO chown -R root:root $SETTINGS_DIR
$SUDO chown -R omnibot:omnibot /tmp/flask_session 2>/dev/null || $SUDO chown -R root:root /tmp/flask_session
$SUDO chmod 600 $SETTINGS_DIR/settings.json
$SUDO chmod 755 /tmp/flask_session

echo "[7/8] Creating systemd service..."
$SUDO tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=OMNIBOT v2.7 Titan Trading Dashboard
After=network.target

[Service]
Type=simple
User=omnibot
Group=omnibot
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$VENV_DIR/bin
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

$SUDO systemctl daemon-reload
$SUDO systemctl enable $SERVICE_NAME

echo "[8/8] Starting service..."
$SUDO systemctl start $SERVICE_NAME

echo ""
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8081"
echo "Login: admin / admin"
echo ""
echo "Commands:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo systemctl restart $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Settings file: $SETTINGS_DIR/settings.json"
echo "Install directory: $INSTALL_DIR"
echo ""
